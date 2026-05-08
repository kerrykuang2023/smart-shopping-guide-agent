from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.models import ChatMessage, Product, RuntimeSettings


class ChatService:
    """
    智能导购对话服务
    将产品信息转化为有感染力、有情绪价值的销售话术
    支持多轮对话上下文
    """

    def answer(
        self, 
        product: Product, 
        message: str, 
        settings: RuntimeSettings,
        history: list[ChatMessage] = None
    ) -> tuple[str, bool, str]:
        """
        生成导购回复，支持对话历史上下文
        
        Args:
            product: 产品信息
            message: 当前用户消息
            settings: 运行时设置
            history: 对话历史（可选）
        
        Returns:
            (answer_text, is_mocked, source)
        """
        history = history or []
        
        # 优先使用远程 LLM 生成自然话术
        if settings.llm_base_url.strip():
            remote = self._answer_with_sales_llm(product, message, settings, history)
            if remote:
                return remote, False, "remote_llm"

        # Fallback: 使用本地模板生成话术（简化版，忽略历史）
        return self._generate_sales_pitch(product, message), True, "knowledge_base"

    @staticmethod
    def _build_sales_system_prompt() -> str:
        """
        构建金牌导购的系统提示词
        强调情绪价值、销售技巧和自然对话
        """
        return """你是一位经验丰富的金牌门店导购，擅长用热情、专业且有感染力的方式向顾客介绍产品。

【你的风格特点】
1. **热情亲和**：像对待朋友一样，用"您"称呼，语气温暖不机械
2. **突出价值**：不只讲功能，更要讲"这能给您带来什么好处"
3. **场景代入**：描述具体使用场景，让顾客能想象拥有后的体验
4. **情感共鸣**：用"说实话""不瞒您说"等口语化表达，建立信任
5. **自然过渡**：不要罗列123，要像聊天一样流畅自然
6. **促成行动**：适时给出购买建议，但不强迫

【回答结构】（灵活组合，不要生硬套用）
- 开场：认可顾客的问题/需求
- 主体：结合产品特色，讲一个"卖点故事"
- 价值：为什么这个特点对顾客重要
- 对比：轻描淡写地提及竞品优势（如有）
- 收尾：给出购买建议或邀请体验

【禁止事项】
- 不要机械罗列"第一、第二、第三"
- 不要直接读出技术参数
- 不要编造库存、价格、促销活动
- 不要过度承诺

记住：你是在帮顾客解决问题，而不只是卖东西。"""

    @staticmethod
    def _build_product_context(product: Product) -> str:
        """
        构建产品上下文信息，包含销售所需的全部素材
        """
        # 卖点整理
        selling_points = []
        for sp in product.selling_points:
            point_text = sp.text
            if sp.image:
                point_text += f"（配图：{sp.image}）"
            selling_points.append(point_text)
        
        # 竞品优势对比
        competitor_info = []
        for comp in product.competitors:
            advantages = comp.our_advantages or []
            their_advantages = comp.their_advantages or []
            comp_text = f"vs {comp.name}："
            if advantages:
                comp_text += f"我们的优势是{'、'.join(advantages)}"
            if their_advantages:
                comp_text += f"；对方优势是{'、'.join(their_advantages)}"
            competitor_info.append(comp_text)
        
        # 关联推荐
        related_items = []
        for rel in product.related_products:
            reason = f"{rel.name}"
            if rel.reason:
                reason += f"（{rel.reason}）"
            related_items.append(reason)
        
        # 使用场景
        use_cases = product.use_cases or []
        target_users = product.target_users or []
        
        context = f"""
【产品基本信息】
- 名称：{product.name}
- 品牌：{product.brand}
- 品类：{product.category}
- 价格：{f"¥{product.price}" if product.price else "咨询店员"}

【核心卖点】
{chr(10).join(f"- {sp}" for sp in selling_points)}

【适用场景】
{chr(10).join(f"- {uc}" for uc in use_cases) if use_cases else "- 日常办公/学习使用"}

【适合人群】
{chr(10).join(f"- {tu}" for tu in target_users) if target_users else "- 广泛适用"}

【竞品对比】
{chr(10).join(f"- {ci}" for ci in competitor_info) if competitor_info else "- 暂无对比信息"}

【搭配推荐】
{chr(10).join(f"- {ri}" for ri in related_items) if related_items else "- 暂无搭配推荐"}
"""
        return context

    @staticmethod
    def _answer_with_sales_llm(
        product: Product, 
        message: str, 
        settings: RuntimeSettings,
        history: list[ChatMessage] = None
    ) -> str | None:
        """
        使用远程 LLM 生成销售话术，支持对话历史上下文
        """
        endpoint = settings.llm_base_url.rstrip("/")
        if not endpoint.endswith("/v1/chat/completions"):
            endpoint = f"{endpoint}/v1/chat/completions"

        product_context = ChatService._build_product_context(product)
        system_prompt = ChatService._build_sales_system_prompt()

        # 构建消息列表，包含历史对话
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{product_context}\n\n【当前对话背景】\n你正在向顾客介绍上述产品。请基于历史对话和当前问题，用金牌导购的方式自然回应，不要重复已经讲过的内容。"},
        ]
        
        # 添加历史对话
        if history:
            for msg in history[-6:]:  # 只保留最近6轮，避免超出 token 限制
                messages.append({
                    "role": "assistant" if msg.role == "ai" else msg.role,
                    "content": msg.content
                })
        
        # 添加当前问题
        messages.append({
            "role": "user",
            "content": f"【顾客的新问题】\n{message}\n\n请自然回应，像跟朋友聊天一样，不要机械重复之前的介绍。",
        })

        payload = {
            "model": settings.llm_model,
            "temperature": 0.7,
            "max_tokens": 500,
            "messages": messages,
        }
        
        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        
        req = urllib.request.Request(
            endpoint, 
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), 
            headers=headers, 
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, TimeoutError, OSError, KeyError, IndexError, json.JSONDecodeError):
            return None

    @staticmethod
    def _generate_sales_pitch(product: Product, message: str) -> str:
        """
        本地生成销售话术（当 LLM 不可用时使用）
        比原来的模板更自然、更有感染力
        """
        import random
        
        # 开场白池
        openings = [
            f"您问得真好！{product.name} 确实是我们的明星产品，",
            f"哈哈，看得出来您对{product.category}很有研究！",
            f"说实话，{product.name} 我自己也在用，",
            f"您眼光不错！这款产品特别适合您，",
        ]
        
        # 价值强调句式
        value_patterns = [
            "不只是{feature}，更重要的是{benefit}",
            "很多顾客反馈，用了之后{benefit}",
            "您可能觉得{feature}没什么，但实际用起来{benefit}",
        ]
        
        # 结尾建议
        closings = [
            "您可以亲自体验一下，感受会不一样。",
            "现在入手挺合适的，售后也有保障。",
            "要不要我帮您拿一支试试手感？",
        ]
        
        # 构建卖点描述
        point_texts = []
        for sp in product.selling_points[:2]:  # 只取前2个卖点，避免啰嗦
            # 从卖点文本中提取关键词
            text = sp.text
            # 尝试构建价值句式
            if "顺滑" in text or "流畅" in text:
                point_texts.append(f"书写特别顺滑，长时间写字手不会累")
            elif "速干" in text or "干" in text:
                point_texts.append(f"墨水干得很快，写完不会蹭花")
            elif "握" in text or "舒适" in text:
                point_texts.append(f"握感很舒服，用久了手也不酸")
            elif "色" in text or "鲜艳" in text:
                point_texts.append(f"颜色很正，做标记特别醒目")
            else:
                point_texts.append(text)
        
        main_pitch = "；".join(point_texts) if point_texts else product.selling_points[0].text if product.selling_points else "品质很过硬"
        
        # 竞品对比（轻描淡写）
        competitor_text = ""
        if product.competitors:
            comp = product.competitors[0]
            if comp.our_advantages:
                advantage = comp.our_advantages[0]
                competitor_text = f"跟{comp.name}比起来，{advantage}。"
        
        # 搭配推荐
        related_text = ""
        if product.related_products:
            rels = product.related_products[:2]
            if len(rels) == 2:
                related_text = f"对了，很多顾客还会搭配{rels[0].name}和{rels[1].name}一起买，用着更顺手。"
            else:
                related_text = f"对了，搭配{rels[0].name}一起用效果会更好。"
        
        # 组装话术
        parts = [
            random.choice(openings),
            main_pitch + "。",
        ]
        
        if competitor_text:
            parts.append(competitor_text)
        
        if related_text:
            parts.append(related_text)
        
        parts.append(random.choice(closings))
        
        return "".join(parts)

    def general_answer(
        self, 
        message: str, 
        settings: RuntimeSettings,
        history: list[ChatMessage] = None
    ) -> tuple[str, bool, str]:
        """
        通用对话回复（当商品未在知识库中识别时使用），支持对话历史
        
        Returns:
            (answer_text, is_mocked, source)
        """
        history = history or []
        
        # 优先使用远程 LLM 生成回复
        if settings.llm_base_url.strip():
            remote = self._answer_with_general_llm(message, settings, history)
            if remote:
                return remote, False, "remote_llm"
        
        # Fallback: 使用本地模板生成友好的通用回复（简化版，忽略历史）
        return self._generate_general_response(message), True, "general_knowledge"
    
    @staticmethod
    def _build_general_system_prompt() -> str:
        """
        构建通用对话的系统提示词
        当无法识别具体商品时，以友善的通用助手身份回复
        """
        return """你是一位友善的购物助手。虽然用户展示的商品不在你的商品库中，但你仍然可以：

【你的态度】
1. **坦诚告知**：首先礼貌地说明这个商品不在当前库中
2. **积极帮助**：表示愿意基于通用知识尽力帮助
3. **专业建议**：根据用户的描述，给出合理的购物建议
4. **引导探索**：如果有相关商品，可以引导用户了解

【回答结构】
- 开场：坦诚说明 + 表达帮助意愿
- 主体：基于通用购物知识给出建议
- 收尾：邀请用户继续提问或查看相关推荐

【注意事项】
- 不要编造具体的商品参数或价格
- 可以分享通用的选购原则
- 保持热情友善的语气
- 如果完全不了解，诚实说明并询问更多信息"""
    
    def _answer_with_general_llm(
        self, 
        message: str, 
        settings: RuntimeSettings,
        history: list[ChatMessage] = None
    ) -> str | None:
        """
        调用远程 LLM 进行通用对话，支持对话历史上下文
        """
        try:
            system_prompt = self._build_general_system_prompt()
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            
            # 添加历史对话
            if history:
                for msg in history[-6:]:
                    messages.append({
                        "role": "assistant" if msg.role == "ai" else msg.role,
                        "content": msg.content
                    })
            
            # 添加当前问题
            messages.append({
                "role": "user", 
                "content": f"【用户新问题】\n{message}\n\n请基于对话历史和通用知识，自然回应，不要重复之前的内容。"
            })
            
            payload = {
                "model": settings.llm_model or "qwen-plus",
                "temperature": 0.7,
                "messages": messages,
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.llm_api_key}",
            }
            
            req = urllib.request.Request(
                f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception:
            return None
    
    @staticmethod
    def _generate_general_response(message: str) -> str:
        """
        生成本地通用回复（当 LLM 不可用时使用）
        """
        import random
        
        # 常见购物咨询的通用回复模板
        templates = [
            "您好！这个商品确实不在我们当前的产品库中，但我可以从通用的角度帮您分析一下。",
            "抱歉，我暂时还没收录这款商品，不过我很乐意基于购物经验给您一些建议。",
            "这个商品我暂时不认识，但这不妨碍我帮您！让我想想...",
        ]
        
        # 通用建议
        advice_list = [
            "选购这类商品，一般建议先看品牌口碑和用户评价。",
            "如果预算允许，建议选择知名品牌，质量和售后更有保障。",
            "这类商品建议关注材质和做工，细节决定使用体验。",
            "购买前最好对比一下不同渠道的价格和服务。",
        ]
        
        closing_list = [
            "如果您有这款商品的更多信息，欢迎继续问我！",
            "如果您对我们库中的其他商品感兴趣，也可以随时问我。",
            "有什么其他问题，我随时在这里帮您！",
        ]
        
        # 分析用户问题类型，给出相关建议
        user_lower = message.lower()
        advice = random.choice(advice_list)
        
        if "价" in user_lower or "钱" in user_lower or "贵" in user_lower or "便宜" in user_lower:
            advice = "价格方面，建议多比较几个渠道，同时注意是否有促销活动。"
        elif "好" in user_lower or "推荐" in user_lower or "怎样" in user_lower:
            advice = "选购时建议优先考虑品牌的口碑和产品的实际评价。"
        elif "用" in user_lower or "功能" in user_lower or "怎么" in user_lower:
            advice = "具体使用方法建议查看产品说明书，或者询问销售人员。"
        
        return (
            random.choice(templates) + "\n\n" +
            advice + "\n\n" +
            random.choice(closing_list)
        )
