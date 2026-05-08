"""
一次性探测多轮对话 API 表现（无外部 LLM 时的本地回退路径）。
用法: 在后端目录执行  python scripts/multiround_chat_probe.py
报告写入 backend/multiround_probe_report.json
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

SKU = "pilot-g2-black-0.7"


def run_scenario(name: str, sku: str | None, turns: list[str]) -> dict:
    print("=" * 72)
    print(name)
    print("=" * 72)
    history: list[dict] = []
    summary = None
    transcript: list[dict] = []
    with TestClient(app) as client:
        for i, msg in enumerate(turns, 1):
            body: dict = {"message": msg, "history": history, "summary": summary}
            if sku:
                body["sku"] = sku
            r = client.post("/api/v1/chat", json=body)
            if r.status_code != 200:
                return {"error": f"turn {i} HTTP {r.status_code}", "body": r.text}
            data = r.json()
            turn_rec = {
                "turn": i,
                "user": msg,
                "assistant": data["answer"],
                "mocked": data.get("mocked"),
                "source": data.get("source"),
            }
            transcript.append(turn_rec)
            print(f"\n--- Turn {i} | mocked={data.get('mocked')} source={data.get('source')} ---")
            print(f"[user]\n{msg}\n")
            print(f"[assistant]\n{data['answer']}\n")
            history = data.get("history") or []
            summary = data.get("summary")
    return {"scenario": name, "sku": sku, "turns": transcript}


def main() -> None:
    out_path = Path(__file__).resolve().parent.parent / "multiround_probe_report.json"
    general_turns = [
        "你好，我在展台上有点懵，不知道该怎么选中性笔。",
        "孩子小学三年级，主要写作业，想顺滑一点的。",
        "你刚才说的我有点担心价格，有没有不伤纸又不要太贵的？",
        "那我直接问你吧：我手汗多，笔杆老滑怎么办？",
    ]
    sku_turns = [
        "这支笔大概能写多久？",
        "比起晨光那种，值得多花这钱吗？",
        "好的，那你觉得我刚刚担心的点你解决了吗？",
        "最后帮我一句总结，我老婆让我带一支回去，我怎么说？",
    ]

    report = {
        "a_general_no_sku": run_scenario(
            "A. 通用对话（无 SKU，未识图路径）",
            None,
            general_turns,
        ),
        "b_product_sku": run_scenario(
            "B. 单品导购（有 SKU，本地模板回退）",
            SKU,
            sku_turns,
        ),
        "environment_note": "mocked=true: 未配置 LLM URL，走本地模板；此路径多轮记忆未传入生成函数。",
    }
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nWrote:", out_path)


if __name__ == "__main__":
    main()
