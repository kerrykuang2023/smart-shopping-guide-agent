#!/usr/bin/env python3
"""
ChatService 手动测试脚本
"""
import sys
sys.path.insert(0, 'D:\\workspace\\cursorspace\\smart-shopping-guide-agent\\backend')

from app.services.chat import ChatService
from app.models import Product, RuntimeSettings, SellingPoint, ProductRef

def test_basic():
    """基本功能测试"""
    print("=" * 60)
    print("测试 1: 基本话术生成")
    print("=" * 60)
    
    service = ChatService()
    product = Product(
        sku="chenguang-k35",
        name="晨光 K35 中性笔",
        category="签字笔",
        brand="晨光",
        price=12.9,
        primary_image="test.jpg",
        selling_points=[
            SellingPoint(text="0.5mm子弹头笔尖，书写顺滑不断墨"),
            SellingPoint(text="速干墨水，写完即干不蹭花"),
            SellingPoint(text="人体工学握笔设计，长时间书写不疲劳"),
        ],
        competitors=[
            ProductRef(
                sku="deli-s01",
                name="得力 S01",
                image="test.jpg",
                our_advantages=["握感更舒适"],
                their_advantages=["价格更低"]
            )
        ],
        related_products=[
            ProductRef(sku="notebook", name="晨光笔记本", image="test.jpg", reason="搭配使用")
        ]
    )
    settings = RuntimeSettings(llm_base_url="")
    
    answer, mocked, source = service.answer(product, "这支笔怎么样？", settings)
    print(f"问题: 这支笔怎么样？")
    print(f"回答: {answer}")
    print(f"来源: {source}")
    print(f"是否本地模式: {mocked}")
    print()
    
    # 验证回答质量
    checks = {
        "包含产品名": "晨光 K35" in answer or "K35" in answer,
        "不是机械罗列": "第一" not in answer and "第二" not in answer,
        "有自然开场": any(w in answer for w in ["您", "哈哈", "说实话", "您眼光"]),
        "有价值强调": any(w in answer for w in ["顺滑", "不蹭花", "不疲劳", "舒服"]),
    }
    
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
    
    return all(checks.values())


def test_comparison():
    """竞品对比测试"""
    print()
    print("=" * 60)
    print("测试 2: 竞品对比话术")
    print("=" * 60)
    
    service = ChatService()
    product = Product(
        sku="pilot-g2",
        name="百乐 G2 中性笔",
        category="签字笔",
        brand="百乐",
        price=15.8,
        primary_image="test.jpg",
        selling_points=[SellingPoint(text="G2 凝胶墨水，色彩饱满")],
        competitors=[
            ProductRef(
                sku="chenguang",
                name="晨光 K35",
                image="test.jpg",
                our_advantages=["墨水更鲜艳"],
                their_advantages=["更便宜"]
            )
        ]
    )
    settings = RuntimeSettings(llm_base_url="")
    
    answer, _, _ = service.answer(product, "和晨光的比哪个好？", settings)
    print(f"问题: 和晨光的比哪个好？")
    print(f"回答: {answer}")
    print()
    
    # 验证是否提到竞品
    has_competitor = "晨光" in answer or "K35" in answer
    print(f"  {'✅' if has_competitor else '❌'} 提到竞品")
    
    return has_competitor


def test_variations():
    """测试回复多样性"""
    print()
    print("=" * 60)
    print("测试 3: 回复多样性")
    print("=" * 60)
    
    service = ChatService()
    product = Product(
        sku="test",
        name="测试笔",
        category="测试",
        brand="测试品牌",
        primary_image="test.jpg",
        selling_points=[SellingPoint(text="测试卖点")]
    )
    settings = RuntimeSettings(llm_base_url="")
    
    answers = []
    for i in range(5):
        answer, _, _ = service.answer(product, "怎么样？", settings)
        answers.append(answer)
    
    # 检查是否有变化
    unique_answers = len(set(answers))
    print(f"生成 5 次回复，其中 {unique_answers} 个不同")
    
    for i, ans in enumerate(answers, 1):
        print(f"  {i}. {ans[:50]}...")
    
    has_variation = unique_answers > 1
    print(f"  {'✅' if has_variation else '❌'} 开场白有变化")
    
    return has_variation


def test_fallback():
    """测试 LLM 回退"""
    print()
    print("=" * 60)
    print("测试 4: LLM 不可达时回退到本地模式")
    print("=" * 60)
    
    service = ChatService()
    product = Product(
        sku="test",
        name="测试笔",
        category="测试",
        brand="测试品牌",
        primary_image="test.jpg",
        selling_points=[SellingPoint(text="测试卖点")]
    )
    # 配置一个无效的 LLM URL
    settings = RuntimeSettings(
        llm_base_url="http://localhost:99999/invalid",
        llm_api_key="test",
        llm_model="test"
    )
    
    answer, mocked, source = service.answer(product, "测试问题", settings)
    print(f"配置无效 LLM URL，实际来源: {source}")
    print(f"回答: {answer}")
    print(f"是否回退到本地: {mocked}")
    print(f"  {'✅' if mocked else '❌'} 正确回退到本地模式")
    
    return mocked


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("ChatService 销售话术测试")
    print("=" * 60 + "\n")
    
    results = []
    
    try:
        results.append(("基本话术生成", test_basic()))
        results.append(("竞品对比话术", test_comparison()))
        results.append(("回复多样性", test_variations()))
        results.append(("LLM回退", test_fallback()))
        
        print()
        print("=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        
        for name, passed in results:
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"  {status}: {name}")
        
        all_passed = all(r[1] for r in results)
        print()
        if all_passed:
            print("🎉 所有测试通过！ChatService 工作正常。")
            return 0
        else:
            print("⚠️ 部分测试失败，请检查代码。")
            return 1
            
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
