# Smart Shopping Guide Agent (智能导购 Agent)

> An AI-powered product guide agent that turns every customer interaction into a professional sales experience. Part of the **KWeaver Box** edge AI platform.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-MVP-orange.svg)]()

## 项目简介

**智能导购 Agent** 是 KWeaver Box 边缘 AI 平台上的首个标杆应用。它通过视觉识别 + 大语言模型，让任意零售/4S 店/家电卖场/医疗器械展厅的导购员（或顾客自助）都能获得"金牌销售"级别的专业讲解。

### Use Cases

| 行业 | 场景 |
|------|------|
| 零售门店 | 顾客拍照识别商品，AI 讲解卖点和促销 |
| 4S 店 | 看车人扫描车型，AI 介绍配置和对比竞品 |
| 家电卖场 | 选购对比，AI 推荐搭配和优惠组合 |
| 医疗器械展厅 | 专业产品讲解，降低对销售人员依赖 |
| 博物馆/展会 | 文物/展品识别讲解 |

## 核心能力

- **视觉识别**：手机/平板拍照即识别产品 SKU（基于 Qwen2.5-VL）
- **专业讲解**：基于产品知识库生成卖点讲解（文字 + 语音）
- **互动问答**：顾客追问，AI 实时回答
- **竞品对比**：一键对比同类竞品优劣势
- **关联推荐**：搭配套餐、优惠组合、以旧换新
- **完全离线**：部署在边缘端（FusionXpark/DGX Spark），数据不出店

## 技术架构

```
┌─────────────────────────────────────────┐
│  前端 (Phone / Tablet)                   │
│  - H5 (Vue 3) ← 验证阶段                  │
│  - Native App (Flutter) ← 企业部署        │
└───────────────────┬─────────────────────┘
                    │ HTTP / WebSocket
                    ▼
┌─────────────────────────────────────────┐
│  后端 (FusionXpark GB10 / Edge Box)      │
│  - FastAPI Service                       │
│  - Qwen2.5-VL (视觉识别)                  │
│  - LLM Agent (讲解生成)                  │
│  - Knowledge Base (Qdrant)              │
└─────────────────────────────────────────┘
```

详细架构请参见 [docs/architecture.md](docs/architecture.md)

## 项目结构

```
smart-shopping-guide-agent/
├── backend/              # FastAPI 后端服务（部署在 GB10）
├── frontend-h5/          # H5 快速验证版（Vue 3）
├── frontend-app/         # Flutter 原生 App（企业部署版）
├── knowledge/            # 产品知识库模板与示例
├── deployment/           # 部署配置（1Panel/Docker/Helm）
└── docs/                 # 设计文档与 API 规范
```

## 快速开始

### 后端服务（GB10/Docker）

```bash
cd backend
docker build -t smart-guide-agent:latest .
docker run --gpus all -p 8080:8080 smart-guide-agent:latest
```

### H5 验证版

```bash
cd frontend-h5
npm install
npm run dev
# 手机扫码访问 http://<你的IP>:5173
```

### 1Panel 一键部署

将 `deployment/1panel/` 目录复制到 1Panel 的本地应用目录：

```bash
sudo cp -r deployment/1panel/smart-guide-agent /opt/1panel/resource/apps/local/
# 在 1Panel 应用商店刷新即可看到，一键安装
```

详细部署步骤参见 [deployment/README.md](deployment/README.md)

## 路线图

- [x] 项目初始化
- [ ] **Phase 1 - MVP（第 1 周）**：H5 验证版 + 后端基础服务，3-5 个 SKU 识别
- [ ] **Phase 2 - 企业版（第 2-3 周）**：Flutter App + 离线缓存 + 1Panel 应用包
- [ ] **Phase 3 - 知识库扩展**：支持 100+ SKU、ERP 集成、ROI 看板
- [ ] **Phase 4 - 多模态升级**：语音对话、扫码枪集成、多语言

## 关于 KWeaver Box

KWeaver Box 是面向企业现场的边缘 AI 操作系统，以"算力盒子 + AppHub 平台 + 数字员工应用（.kwapp）"为核心形态。本项目作为 KWeaver Box 的首批标杆 .kwapp 应用，验证整个平台的端到端能力。

更多信息：[https://github.com/kweaver-ai/](https://github.com/kweaver-ai/)

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
