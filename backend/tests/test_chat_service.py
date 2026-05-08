#!/usr/bin/env python3
"""
ChatService 测试
验证销售话术生成功能
"""

import pytest
from app.models import Product, RuntimeSettings, SellingPoint, ProductRef, GalleryImage
from app.services.chat import ChatService


class TestChatServiceLocalMode:
    """测试本地话术生成模式（无需 LLM）"""

    @pytest.fixture
    def chat_service(self):
        return ChatService()

    @pytest.fixture
    def sample_product(self):
        """创建测试产品"""
        return Product(
            sku="chenguang-k35",
            name="晨光 K35 中性笔",
            category="签字笔",
            brand="晨光",
            price=12.9,
            primary_image="chenguang-k35-hero.jpg",
            selling_points=[
                SellingPoint(text="0.5mm子弹头笔尖，书写顺滑不断墨"),
                SellingPoint(text="速干墨水，写完即干不蹭花"),
                SellingPoint(text="人体工学握笔设计，长时间书写不疲劳"),
            ],
            gallery=[
                GalleryImage(url="chenguang-k35-front.jpg", angle="正面"),
                GalleryImage(url="chenguang-k35-writing.jpg", angle="书写展示"),
            ],
            specs=["笔尖：0.5mm子弹头", "墨水：速干型", "笔身：人体工学设计"],
            target_users=["学生", "白领", "考试人群"],
            use_cases=["日常书写", "考试答题", "办公记录"],
            related_products=[
                ProductRef(
                    sku="deli-s01",
                    name="得力 S01 中性笔",
                    image="deli-s01-hero.jpg",
                    price=9.9,
                    reason="性价比之选"
                )
            ],
            competitors=[
                ProductRef(
                    sku="deli-s01",
                    name="得力 S01",
                    image="deli-s01-hero.jpg",
                    our_advantages=["握感更舒适", "墨水更顺滑"],
                    their_advantages=["价格更低"]
                )
            ]
        )

    @pytest.fixture
    def empty_settings(self):
        """空配置（触发本地模式）"""
        return RuntimeSettings(
            llm_base_url="",  # 空 URL 触发本地模式
            llm_api_key="",
            llm_model=""
        )

    def test_local_mode_triggered_when_no_llm_url(self, chat_service, sample_product, empty_settings):
        """测试：当 LLM URL 为空时，使用本地模式"""
        answer, is_mocked, source = chat_service.answer(
            sample_product, 
            "这支笔怎么样？", 
            empty_settings
        )
        
        assert is_mocked is True
        assert source == "knowledge_base"
        assert len(answer) > 0
        print(f"\n本地模式回复: {answer}\n")

    def test_sales_pitch_structure(self, chat_service, sample_product, empty_settings):
        """测试：销售话术结构是否自然"""
        answer, _, _ = chat_service.answer(
            sample_product,
            "这支笔好用吗？",
            empty_settings
        )
        
        # 检查不是机械罗列
        assert "第一" not in answer or "核心卖点是" not in answer
        assert "第二" not in answer
        assert "第三" not in answer
        
        # 检查有自然开场
        natural_openings = ["您", "哈哈", "说实话", "您眼光"]
        has_natural_opening = any(op in answer for op in natural_openings)
        assert has_natural_opening, f"回复缺少自然开场: {answer}"

    def test_value_emphasis_not_features(self, chat_service, sample_product, empty_settings):
        """测试：强调价值而非功能"""
        answer, _, _ = chat_service.answer(
            sample_product,
            "这支笔有什么特点？",
            empty_settings
        )
        
        # 应该突出好处，而非罗列参数
        # 检查是否将"0.5mm"转化为"书写顺滑"
        # 检查是否将"速干墨水"转化为"不蹭花"
        value_words = ["顺滑", "不蹭花", "不疲劳", "舒服", "体验"]
        has_value_emphasis = any(vw in answer for vw in value_words)
        assert has_value_emphasis, f"回复缺少价值强调: {answer}"

    def test_product_name_included(self, chat_service, sample_product, empty_settings):
        """测试：回复中包含产品名"""
        answer, _, _ = chat_service.answer(
            sample_product,
            "推荐一支笔",
            empty_settings
        )
        
        assert "晨光 K35" in answer or "K35" in answer

    def test_different_questions_different_responses(self, chat_service, sample_product, empty_settings):
        """测试：不同问题有不同回复"""
        answer1, _, _ = chat_service.answer(sample_product, "这支笔怎么样？", empty_settings)
        answer2, _, _ = chat_service.answer(sample_product, "和得力的比哪个好？", empty_settings)
        
        # 两个回复应该不同
        assert answer1 != answer2
        
        # 竞品对比问题应该提到竞品
        assert "得力" in answer2 or "S01" in answer2

    def test_short_product_handling(self, chat_service, empty_settings):
        """测试：最少信息产品的处理"""
        minimal_product = Product(
            sku="test-001",
            name="测试笔",
            category="测试",
            brand="测试品牌",
            primary_image="test.jpg",
            selling_points=[SellingPoint(text="这是一个测试卖点")]
        )
        
        answer, _, _ = chat_service.answer(
            minimal_product,
            "这是什么？",
            empty_settings
        )
        
        assert len(answer) > 0
        assert "测试笔" in answer


class TestChatServiceLLMMode:
    """测试 LLM 模式（需要外部 API）"""

    @pytest.fixture
    def chat_service(self):
        return ChatService()

    @pytest.fixture
    def sample_product(self):
        return Product(
            sku="pilot-g2",
            name="百乐 G2 中性笔",
            category="签字笔",
            brand="百乐",
            price=15.8,
            primary_image="pilot-g2-hero.jpg",
            selling_points=[
                SellingPoint(text="G2 凝胶墨水，色彩饱满"),
                SellingPoint(text="防滑橡胶握把"),
            ]
        )

    @pytest.fixture
    def llm_settings(self):
        """配置 LLM（使用一个不存在的 URL 测试 fallback）"""
        return RuntimeSettings(
            llm_base_url="http://localhost:9999/test",  # 无效 URL
            llm_api_key="test-key",
            llm_model="test-model"
        )

    def test_llm_mode_fallback_when_unreachable(self, chat_service, sample_product, llm_settings):
        """测试：LLM 不可达时回退到本地模式"""
        answer, is_mocked, source = chat_service.answer(
            sample_product,
            "这支笔怎么样？",
            llm_settings
        )
        
        # LLM 不可达时应该回退到本地模式
        assert is_mocked is True
        assert source == "knowledge_base"
        assert len(answer) > 0
        print(f"\nLLM回退模式回复: {answer}\n")


class TestSalesPitchTemplates:
    """测试销售话术模板"""

    @pytest.fixture
    def chat_service(self):
        return ChatService()

    def test_opening_variations(self, chat_service):
        """测试：开场白有变化"""
        product = Product(
            sku="test-001",
            name="测试产品",
            category="测试",
            brand="测试品牌",
            primary_image="test.jpg",
            selling_points=[SellingPoint(text="卖点1")]
        )
        settings = RuntimeSettings(llm_base_url="")
        
        # 多次生成，检查开场白有变化
        openings = set()
        for _ in range(10):
            answer, _, _ = chat_service.answer(product, "怎么样？", settings)
            # 提取前10个字作为开场标识
            opening = answer[:10]
            openings.add(opening)
        
        # 至少应该有2种不同的开场
        assert len(openings) >= 2, f"开场白过于单一: {openings}"

    def test_feature_to_benefit_conversion(self, chat_service):
        """测试：功能点转化为价值描述"""
        test_cases = [
            ("0.5mm笔尖", ["顺滑", "书写", "流畅"]),
            ("速干墨水", ["干", "蹭", "花"]),
            ("人体工学", ["握", "舒服", "累"]),
            ("防滑", ["握", "稳"]),
        ]
        
        for feature, expected_keywords in test_cases:
            product = Product(
                sku="test-001",
                name="测试笔",
                category="测试",
                brand="测试品牌",
                primary_image="test.jpg",
                selling_points=[SellingPoint(text=feature)]
            )
            settings = RuntimeSettings(llm_base_url="")
            
            answer, _, _ = chat_service.answer(product, "这支笔怎么样？", settings)
            
            # 检查是否包含至少一个价值关键词
            has_keyword = any(kw in answer for kw in expected_keywords)
            print(f"\n功能'{feature}' -> 回复: {answer[:50]}...")
            assert has_keyword, f"功能'{feature}'未转化为价值描述"


class TestEdgeCases:
    """测试边界情况"""

    @pytest.fixture
    def chat_service(self):
        return ChatService()

    def test_empty_message(self, chat_service):
        """测试：空消息处理"""
        product = Product(
            sku="test-001",
            name="测试产品",
            category="测试",
            brand="测试品牌",
            primary_image="test.jpg",
            selling_points=[SellingPoint(text="卖点")]
        )
        settings = RuntimeSettings(llm_base_url="")
        
        # 空字符串应该返回有效回复
        answer, _, _ = chat_service.answer(product, "", settings)
        assert len(answer) > 0

    def test_long_message(self, chat_service):
        """测试：长消息处理"""
        product = Product(
            sku="test-001",
            name="测试产品",
            category="测试",
            brand="测试品牌",
            primary_image="test.jpg",
            selling_points=[SellingPoint(text="卖点")]
        )
        settings = RuntimeSettings(llm_base_url="")
        
        long_message = "我想买一支笔，用来写日记，要求书写流畅，不晕染，握感舒适，价格不要太贵，请问这款怎么样？"
        answer, _, _ = chat_service.answer(product, long_message, settings)
        assert len(answer) > 0

    def test_unicode_message(self, chat_service):
        """测试：包含 emoji 和特殊字符的消息"""
        product = Product(
            sku="test-001",
            name="测试产品",
            category="测试",
            brand="测试品牌",
            primary_image="test.jpg",
            selling_points=[SellingPoint(text="卖点")]
        )
        settings = RuntimeSettings(llm_base_url="")
        
        emoji_message = "这支笔✏️适合学生👨‍🎓用吗？"
        answer, _, _ = chat_service.answer(product, emoji_message, settings)
        assert len(answer) > 0

    def test_no_selling_points(self, chat_service):
        """测试：无卖点产品的处理"""
        product = Product(
            sku="test-001",
            name="测试产品",
            category="测试",
            brand="测试品牌",
            primary_image="test.jpg",
            selling_points=[]  # 空卖点
        )
        settings = RuntimeSettings(llm_base_url="")
        
        answer, _, _ = chat_service.answer(product, "怎么样？", settings)
        assert len(answer) > 0
        assert "测试产品" in answer


if __name__ == "__main__":
    # 运行测试并打印详细结果
    pytest.main([__file__, "-v", "-s"])
