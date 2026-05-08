from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.models import ChatMessage, Product, ProductRef, RuntimeSettings


class ChatService:
    """
    智能导购对话服务
    将产品信息转化为有感染力、有情绪价值的销售话术
    支持多轮对话上下文
    """

    def __init__(self) -> None:
        self._llm_debug_snap: dict | None = None

    def pop_llm_debug(self) -> dict | None:
        snap = self._llm_debug_snap
        self._llm_debug_snap = None
        return snap

    def _stash_llm_debug(self, snapshot: dict | None) -> None:
        self._llm_debug_snap = snapshot

    @staticmethod
    def wants_pen_catalog_answer(text: str) -> bool:
        """用户明确在问展位 SKU / 选型推荐时启用（不宜过宽，以免普通闲聊也贴商品卡）。"""
        t = text.strip()
        if not t:
            return False
        keys = (
            "推荐",
            "帮我选",
            "选一支",
            "选一款",
            "哪款",
            "哪只",
            "哪支",
            "介绍一下",
            "展台",
            "陈列",
            "sku",
            "型号",
            "合适的笔",
            "买什么笔",
            "有啥笔",
            "有什么笔",
        )
        return any(k.lower() in t.lower() if k.isascii() else k in t for k in keys)

    @staticmethod
    def suggested_product_refs(message: str, products: list[Product]) -> list[ProductRef]:
        if not products or not ChatService.wants_pen_catalog_answer(message):
            return []
        refs: list[ProductRef] = []
        for p in products:
            reason = p.selling_points[0].text if p.selling_points else None
            refs.append(
                ProductRef(
                    sku=p.sku,
                    name=p.name,
                    image=p.primary_image,
                    price=p.price,
                    reason=reason,
                )
            )
        return refs

    @staticmethod
    def catalog_block_for_llm(products: list[Product]) -> str:
        """注入通用 LLM system 的 SKU 素材块（仅此清单内推荐）。"""
        lines: list[str] = []
        for p in products:
            feats = "；".join(sp.text for sp in p.selling_points[:4])
            price = f"¥{p.price:g}" if p.price is not None else "展台标签为准"
            lines.append(
                f"- SKU=`{p.sku}`｜{p.name}｜{p.brand}｜{price}｜主图 `{p.primary_image}`\n  卖点：{feats or '—'}"
            )
        return "\n".join(lines)

    def answer(
        self, 
        product: Product, 
        message: str, 
        settings: RuntimeSettings,
        history: list[ChatMessage] = None,
        summary: str | None = None
    ) -> tuple[str, bool, str, str | None, list[ChatMessage]]:
        """
        生成导购回复，支持对话历史上下文
        
        Args:
            product: 产品信息
            message: 当前用户消息
            settings: 运行时设置
            history: 对话历史（可选）
            summary: 历史摘要（可选）
        
        Returns:
            (answer_text, is_mocked, source, new_summary, new_history)
        """
        history = history or []
        new_summary, new_history = self._compress_memory(summary, history, settings)
        
        # 优先使用远程 LLM 生成自然话术
        if settings.llm_base_url.strip():
            self._stash_llm_debug(None)
            remote = self._answer_with_sales_llm(
                product, message, settings, new_history, new_summary
            )
            if remote:
                new_history.append(ChatMessage(role="user", content=message))
                new_history.append(ChatMessage(role="assistant", content=remote))
                return remote, False, "remote_llm", new_summary, new_history

        # Fallback: 使用本地模板生成话术（简化版，忽略历史）
        local_answer = self._generate_sales_pitch(product, message, new_history)
        new_history.append(ChatMessage(role="user", content=message))
        new_history.append(ChatMessage(role="assistant", content=local_answer))
        return local_answer, True, "knowledge_base", new_summary, new_history

    def general_answer(
        self,
        message: str,
        settings: RuntimeSettings,
        history: list[ChatMessage] | None = None,
        summary: str | None = None,
        *,
        catalog_products: list[Product] | None = None,
    ) -> tuple[str, bool, str, str | None, list[ChatMessage]]:
        """
        生成通用回复（当未识别到特定商品时）

        catalog_products: 展台全量 SKU，供「推荐」类问题与 LLM 素材注入。
        """
        history = history or []
        catalog_products = catalog_products or []
        new_summary, new_history = self._compress_memory(summary, history, settings)
        cat_block = (
            self.catalog_block_for_llm(catalog_products) if catalog_products else ""
        )

        if settings.llm_base_url.strip():
            self._stash_llm_debug(None)
            remote = self._answer_with_general_llm(
                message,
                settings,
                new_history,
                new_summary,
                catalog_block=cat_block,
            )
            if remote:
                new_history.append(ChatMessage(role="user", content=message))
                new_history.append(ChatMessage(role="assistant", content=remote))
                return remote, False, "remote_llm", new_summary, new_history

        local_answer = self._generate_general_response(
            message, new_history, showcase_products=catalog_products
        )
        new_history.append(ChatMessage(role="user", content=message))
        new_history.append(ChatMessage(role="assistant", content=local_answer))
        return local_answer, True, "general_knowledge", new_summary, new_history

    def _compress_memory(self, summary: str | None, history: list[ChatMessage], settings: RuntimeSettings) -> tuple[str | None, list[ChatMessage]]:
        """
        压缩短期记忆：当历史超过 10 条（5轮）时，将前 6 条（3轮）压缩为摘要
        """
        if len(history) <= 10:
            return summary, history

        old_msgs = history[:6]
        new_history = history[6:]

        if not settings.llm_base_url or not settings.llm_api_key:
            # 如果没有配置 LLM，则直接截断以避免上下文过长
            return summary, new_history

        dialogue_text = "\n".join([f"{'用户' if m.role == 'user' else '导购'}: {m.content}" for m in old_msgs])
        prompt = "你是一个对话历史摘要助手。请将以下历史对话内容进行压缩总结。\n"
        prompt += "要求：\n1. 提取用户关注的核心问题、偏好以及已经讨论过的商品信息。\n2. 保持精简，丢弃寒暄和无关紧要的细节。\n3. 如果有之前的摘要，请将其与新的对话内容合并，形成一个连贯的新摘要。\n\n"

        if summary:
            prompt += f"【之前的摘要】\n{summary}\n\n"

        prompt += f"【新增的对话记录】\n{dialogue_text}\n\n请输出最新的压缩摘要："

        try:
            req_body = {
                "model": settings.llm_model or "qwen-plus",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 500
            }
            req = urllib.request.Request(
                settings.llm_base_url,
                data=json.dumps(req_body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.llm_api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                new_summary = result["choices"][0]["message"]["content"].strip()
                print(f"[Memory] Compressed {len(old_msgs)} messages into summary.")
                return new_summary, new_history
        except Exception as e:
            print(f"[Memory] Compression failed: {e}")
            # 如果压缩失败，直接丢弃旧消息
            return summary, new_history

    @staticmethod
    def _build_sales_system_prompt(summary: str | None = None) -> str:
        """
        构建金牌导购的系统提示词
        强调情绪价值、销售技巧和自然对话
        """
        prompt = """你是一位经验丰富的金牌门店导购，擅长用热情、专业且有感染力的方式向顾客介绍产品。

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
        
        if summary:
            prompt += f"\n\n【之前的对话摘要】\n{summary}\n请在回答时参考上述摘要，保持对话的连贯性，不要重复已经说过的信息。"
            
        return prompt

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

    def _answer_with_sales_llm(
        self,
        product: Product,
        message: str,
        settings: RuntimeSettings,
        history: list[ChatMessage] | None = None,
        summary: str | None = None,
    ) -> str | None:
        """
        使用远程 LLM 生成销售话术，支持对话历史上下文
        """
        endpoint = settings.llm_base_url.rstrip("/")
        if not endpoint.endswith("/v1/chat/completions"):
            endpoint = f"{endpoint}/v1/chat/completions"

        product_context = ChatService._build_product_context(product)
        system_prompt = ChatService._build_sales_system_prompt(summary)

        # 构建消息列表，包含历史对话
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"{product_context}\n\n【当前对话背景】\n"
                    "你正在向顾客介绍上述产品。请基于历史对话和当前问题，用金牌导购的方式自然回应，不要重复已经讲过的内容。"
                ),
            },
        ]

        history = history or []
        # 添加历史对话
        if history:
            for msg in history[-6:]:  # 只保留最近6轮，避免超出 token 限制
                role = msg.role
                if role in ("assistant", "ai"):
                    api_role = "assistant"
                else:
                    api_role = "user"
                messages.append({"role": api_role, "content": msg.content})

        # 添加当前问题
        messages.append(
            {
                "role": "user",
                "content": (
                    f"【顾客的新问题】\n{message}\n\n"
                    "请自然回应，像跟朋友聊天一样，不要机械重复之前的介绍。"
                ),
            },
        )

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
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            self._stash_llm_debug(
                {"mode": "sku_sales", "endpoint": endpoint, "payload": payload}
            )
            return content
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            KeyError,
            IndexError,
            json.JSONDecodeError,
        ):
            self._stash_llm_debug(None)
            return None

    @staticmethod
    def _template_catalog_recommendation(
        showcase_products: list[Product],
        history: list[ChatMessage],
    ) -> str:
        """展位全 SKU 可读推荐（模板），含价格、图像路径引用、卖点。"""
        prior_user_rounds = sum(1 for m in history if m.role == "user")
        lead = (
            "可以，展台这几款都是我们常给顾客试的经典签字笔／中性笔，我按展位真实资料给您对齐一下：\n\n"
            if prior_user_rounds == 0
            else "接上您问的，我从展台 SKU 里给您收窄几支重点款：\n\n"
        )
        chunks: list[str] = []
        for p in showcase_products:
            price = f"¥{p.price:g}" if p.price is not None else "请以展台标价为准"
            feats = [
                sp.text for sp in p.selling_points[:3]
            ] or ["现场试写顺滑与干速最直观"]
            feat_line = "；".join(feats)
            chunks.append(
                f"【{p.name}】（SKU `{p.sku}`）\n"
                f"- 价格：{price}\n"
                f"- 主图（H5 可展示）：{p.primary_image}\n"
                f"- 特点：{feat_line}\n"
            )
        closing = (
            "\n您更在意「写得顺手」「干得快」还是「预算」？说一声我可以帮您从上面再缩到 1～2 支对着试写。"
        )
        return lead + "\n".join(chunks) + closing

    @staticmethod
    def _generate_general_response(
        message: str,
        history: list[ChatMessage] | None = None,
        *,
        showcase_products: list[Product] | None = None,
    ) -> str:
        """
        本地通用导购（未识图 / 无 SKU）：按「展台参谋」视角，少提库、多给可执行建议。
        history 为当前轮之前已确认的往返，不含本条 user message。
        """
        history = history or []
        prior_user_rounds = sum(1 for m in history if m.role == "user")
        text = message.strip()
        t = text.lower()
        showcase_products = showcase_products or []

        if showcase_products and ChatService.wants_pen_catalog_answer(text):
            return ChatService._template_catalog_recommendation(showcase_products, history)

        # —— 意图：尽量覆盖逛展用户的真实问法 ——
        is_child = any(k in text for k in ("孩子", "小学", "作业", "三年级", "学生", "写字"))
        is_price = any(k in t for k in ("价", "钱", "贵", "便宜", "预算", "多花", "省"))
        is_grip = any(k in text for k in ("手汗", "汗", "滑", "握", "笔杆", "脱手", "掐不住"))
        is_compare = any(k in text for k in ("对比", "还是", "哪个", "晨光", "得力", "品牌"))
        is_follow = any(k in text for k in ("刚才", "之前", "你刚", "接上", "上次", "那你"))
        is_how = any(k in text for k in ("怎么选", "不会选", "懵", "不懂", "推荐"))

        # 承接上一轮：用户明确指向对话历史
        follow_lead = ""
        if is_follow and history:
            last_assistant = next((m.content for m in reversed(history) if m.role == "assistant"), "")
            if last_assistant:
                follow_lead = "接着您前面聊的，我把话说得更落地一点。\n\n"

        # 首轮：建立信任，不把用户当成「搜错库」
        if prior_user_rounds == 0:
            lead = (
                "可以，我在展台这边帮您把中性笔怎么选说清楚——先不纠结某一个型号，您按需套就行。\n\n"
            )
            if is_child:
                lead = (
                    "带孩子买笔的家长我见得多，我们先对齐三件事，再下手不晚。\n\n"
                )
            elif is_price:
                lead = "谈预算很实在，我们先分清「标价」和「写得省不省心」这两件事。\n\n"
            elif is_grip:
                lead = "手汗多、笔杆滑这个我懂，优先从「握持」解决，比换牌子更有效。\n\n"
            elif is_how:
                lead = "很多人一进展台懵，很正常。您记三步就够了。\n\n"
        else:
            lead = follow_lead or "接着说，我尽量不重套路话。\n\n"

        # 主体：按意图给结构化建议（可照做）
        body_parts: list[str] = []

        if is_child:
            body_parts.append(
                "• 小学作业：优先看书写顺滑、干得快蹭不蹭卷面，其次看孩子握笔是否省力。\n"
                "• 现场让娃试写两行：笔画多的字也不刮纸，再决定。\n"
                "• 粗细常见 0.5 / 0.7，作业密多用 0.5；想更稳可看略粗的。"
            )
        elif is_grip:
            body_parts.append(
                "• 优先找笔杆带磨砂/橡胶握位或三角矫正区的款式，比光面金属杆更不打滑。\n"
                "• 可先套轻薄笔握套再试写 20 秒，看指腹会不会「蹭出油滑的滑」。\n"
                "• 汗手若严重，随身小毛巾擦拇指食指也比硬换笔省钱。"
            )
        elif is_price:
            body_parts.append(
                "• 不必只看单价：写得顺手、少换芯、少作废作业，长期往往更省时间成本。\n"
                "• 展台上可比「同一沓纸、同一力度」试写，比光看标价客观。\n"
                "• 若预算有限，可先确定「顺滑+干速」底线，再谈品牌层级。"
            )
        elif is_compare:
            body_parts.append(
                "• 现场对比建议同一支笔连续画圈、划线、写名字，感受阻尼和飞白。\n"
                "• 再看替芯是否好买——写顺手却买不到芯，后面更头疼。\n"
                "• 国产入门与进口经典款各有定位，按您对「顺滑 vs 单价」权重选。"
            )
        elif is_how:
            body_parts.append(
                "① 先试写：顺滑、飞白、刮纸。\n"
                "② 等几秒用手背轻蹭，看干速。\n"
                "③ 最后看握感与替芯好不好买。三步里有两步满意，就可以入围。"
            )
        elif is_follow:
            body_parts.append(
                "您刚才同时关心价格与纸质表现的话，可以这样把握：先保证「不蹭卷面」的干速底线，\n"
                "再在同一预算里比较顺滑。纸质偏薄时，干速有时比进口/国产标签更重要。"
            )
        else:
            body_parts.append(
                "• 中性笔核心就看：顺滑、干速、握感、替芯是否好买；四样里先满足您最在意的两样。\n"
                "• 展台试写时别只划一下，写自己常写的字更有参考价值。\n"
                "• 需要我帮您对着货架逐项筛，也可以直接说您的偏向。"
            )

        closing = (
            "\n\n您下一步更想先解决「孩子用的顺滑」还是「预算封顶」？说一声我帮您收窄。"
        )
        if prior_user_rounds >= 2:
            closing = "\n\n还有哪一点不放心，您直说，我按您的原话往下拆。"

        return lead + "\n".join(body_parts) + closing

    @staticmethod
    def _pitch_core_bundle(product: Product) -> tuple[str, str, str]:
        """浓缩卖点、竞品一句、搭配一句（无则空串）。"""
        point_bits: list[str] = []
        for sp in product.selling_points[:2]:
            tx = sp.text
            if "顺滑" in tx or "流畅" in tx:
                point_bits.append("书写顺滑，长时间写也不容易累手")
            elif "速干" in tx or "干" in tx:
                point_bits.append("墨水相对易干，日常书写不容易蹭花")
            elif "握" in tx or "舒适" in tx or "人体工学" in tx or "工学" in tx:
                point_bits.append("握持区设计偏舒适，长时间写也不易累手")
            elif "防滑" in tx:
                point_bits.append("笔杆触感更稳，手汗多也不容易打滑")
            elif "mm" in tx or "笔尖" in tx:
                point_bits.append("笔尖规格适合日常书写，线条粗细好控制")
            else:
                point_bits.append(tx)
        main = "；".join(point_bits) if point_bits else (product.selling_points[0].text if product.selling_points else "口碑与品控都比较稳")

        competitor_text = ""
        if product.competitors:
            c0 = product.competitors[0]
            if c0.our_advantages:
                competitor_text = (
                    f"和{c0.name}比，我们更突出：{'、'.join(c0.our_advantages[:2])}。"
                )

        related_text = ""
        if product.related_products:
            r = product.related_products[:2]
            if len(r) == 2:
                related_text = f"不少客人会顺带带一盒{r[0].name}或{r[1].name}，凑齐全套更顺手。"
            elif r:
                related_text = f"也可以顺手看看{r[0].name}，一起试写对比。"

        return main, competitor_text, related_text

    @staticmethod
    def _generate_sales_pitch(product: Product, message: str, history: list[ChatMessage] | None = None) -> str:
        """
        本地单品导购：必须「先接住问题」再介绍产品，避免复读同一段。
        """
        import random

        history = history or []
        text = message.strip()
        main, competitor_text, related_text = ChatService._pitch_core_bundle(product)

        price_hint = f"展台标价参考大约 ¥{product.price:g}" if product.price else "具体价格以展台标签为准"

        # —— 意图路由 ——
        if any(k in text for k in ("多久", "写不完", "能写", "寿命", "耗尽", "替芯", "笔芯", "换芯")):
            return (
                f"「能写多久」和握笔力度、纸张吃墨都有关，单看照片不好说死。{product.name}这类更适合日常中高频率书写。\n\n"
                f"更实用的判断是看透明窗墨量和出墨是否发涩、断续——断续就该换芯了，别硬写到刮纸。\n\n"
                f"{main}。\n{competitor_text}\n{related_text}\n\n"
                f"需要的话我可以帮您对着实物看一眼墨量，估个使用节奏。"
            ).replace("\n\n\n", "\n\n")

        if any(k in text for k in ("值得", "多花", "性价比", "差别")) or any(
            k in text for k in ("晨光", "得力", "国产", "便宜")
        ):
            opening = random.choice(
                [
                    "这笔钱花得值不值，要看您最吃「顺滑」还是「单价」。",
                    "说实话，价差往往体现在出墨稳定性和长期使用手不累。",
                ]
            )
            return (
                f"{opening}\n\n"
                f"{main}。\n{competitor_text or '您可以现场和常吃的入门款对比试写，看顺滑和飞白'}\n\n"
                f"若您一天写很久，笔感省下来的时间，常比省几块钱更值得。\n{related_text}"
            )

        if any(k in text for k in ("刚才", "担心", "解决", "放心", "你说")):
            return (
                "我理解您想让我把话落到「您能不能放心」——我按您的担心往前推一步。\n\n"
                f"{main}。{competitor_text}\n\n"
                "若您最关心的是孩子写作业不蹭花、手感不累，这款在展台试写的反馈通常比较稳；\n"
                f"仍犹豫的话，我们就用您最常用的写字方式试一下，比听我讲更准。\n{related_text}"
            )

        if any(k in text for k in ("老婆", "老公", "家属", "带回去", "怎么说", "一句", "总结", "交代")):
            return (
                "给您一句能直接带回去交代的话，可按家里人关心点微调：\n\n"
                f"「展台试了这支{product.name}，孩子/我写着顺、干得快不容易蹭纸，{price_hint}。"
                f"家里若更在意价格还是作业整洁，您可以针对性补一句。」\n\n"
                f"若 TA 在意价格，就补「同价位里这笔主要是顺滑省心」；在意作业整洁就补「不蹭卷面」。\n{related_text}"
            )

        # 默认：点题 + 精华介绍（轮换开场）
        pn = product.name
        openings = [
            f"您问到这款{pn}，我先把结论说前面：它是偏「日常长时间写也顺心」的定位。",
            f"这支{pn}我自己也常给顾客试——核心就是写得顺、心里有底。",
        ]
        hook = random.choice(openings)
        return (
            f"{hook}\n\n{main}。\n{competitor_text}\n{related_text}\n\n"
            f"您还想从「价格」「替芯」还是「和孩子作业」哪条再细问？我按那条展开。"
        )

    @staticmethod
    def _build_general_system_prompt(
        summary: str | None = None, *, catalog_block: str = ""
    ) -> str:
        """
        构建通用对话的系统提示词（远程 LLM 用）
        """
        base = """你是线下展区里熟悉中性笔的购物参谋。用户未必拍清某一支笔，你仍要依据下方【展位 SKU 清单】做可执行建议。

【态度】
1. 推荐、对比、选型时：只能引用【展位 SKU 清单】里出现的款；禁止编造清单外的具体型号与价格。
2. 先对齐用户场景（孩子作业/办公/手汗/预算）再建议。
3. 每条推荐写清：笔的全称、大致价位、1～2 条核心特性，并提到主图路径便于顾客在屏上对照。
4. 不确定时引导现场试写三步（顺滑/干速/握感），但不要脱离清单胡编。

【结构】
- 先一句接住用户情绪或场景
- 再给 2～4 条可照做的建议；若用户要推荐，列出 1～2 个清单内 SKU 并说明理由
- 最后一句邀请用户说下一个顾虑点或去试写哪一支
"""
        if catalog_block.strip():
            base += "\n【展位 SKU 清单（权威来源）】\n" + catalog_block.strip() + "\n"
        if summary:
            base += f"\n【此前对话摘要】\n{summary}\n回复时请承接上文，避免重复空话。"
        return base

    def _answer_with_general_llm(
        self,
        message: str,
        settings: RuntimeSettings,
        history: list[ChatMessage] | None = None,
        summary: str | None = None,
        *,
        catalog_block: str = "",
    ) -> str | None:
        """
        调用远程 LLM 进行通用对话，支持对话历史上下文
        """
        endpoint = settings.llm_base_url.rstrip("/")
        if not endpoint.endswith("/v1/chat/completions"):
            endpoint = f"{endpoint}/v1/chat/completions"

        history = history or []
        try:
            system_prompt = self._build_general_system_prompt(
                summary, catalog_block=catalog_block
            )

            messages = [
                {"role": "system", "content": system_prompt},
            ]

            if history:
                for msg in history[-6:]:
                    role = msg.role
                    api_role = "assistant" if role in ("assistant", "ai") else "user"
                    messages.append({"role": api_role, "content": msg.content})

            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"【用户新问题】\n{message}\n\n"
                        "请基于展位 SKU 清单与对话历史自然回应；若要推荐笔，务必从清单中选并写出名称、价格感知与特性。"
                    ),
                }
            )

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
                endpoint,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            self._stash_llm_debug(
                {"mode": "general_llm", "endpoint": endpoint, "payload": payload}
            )
            return content
        except Exception:
            self._stash_llm_debug(None)
            return None
