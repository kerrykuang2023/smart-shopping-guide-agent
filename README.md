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
- **图文并茂讲解**：基于产品知识库生成图片配讲解的卖点呈现
- **互动问答**：顾客追问，AI 实时回答
- **关联推荐**：图片化的搭配套餐、优惠组合
- **竞品对比**：双产品图文对照
- **完全离线**：部署在边缘端（FusionXpark/DGX Spark），数据不出店

## 演示流程一览

> 完整演示脚本见 [`docs/prd.md`](docs/prd.md#12-演示流程设计)

```
1. 演示者打开笔记本浏览器 → http://server:8080
2. 服务端 Console 显示 Dashboard / 知识库管理 / 模型配置
3. 切换到"移动端入口"页面 → 大屏显示 QR Code
4. 观众/客户用手机扫码 → 进入移动端 H5
5. 手机拍摄展台产品 → 后端 AI 识别
6. 手机展示富图片产品卡片 + 关联推荐 + 竞品对比
7. 顾客追问 → AI 流式回答
```

## 技术架构

```
┌─────────────────────────────────────────┐
│  💻 演示者笔记本     📱 观众手机           │
│  (服务端 Console)   (移动端 H5)            │
└──────────────┬──────────────┬────────────┘
               │              │
               │ HTTP / WS    │ HTTP / WS
               ▼              ▼
┌─────────────────────────────────────────┐
│  Edge Box (FusionXpark GB10 / GPU)       │
│  ┌────────────────────────────────────┐ │
│  │  FastAPI 服务（单容器）              │ │
│  │  ├── /     Console SPA              │ │
│  │  ├── /m    Mobile H5 SPA            │ │
│  │  ├── /api  后端 API                 │ │
│  │  └── /images 产品图片                │ │
│  └────────────────────────────────────┘ │
│  ┌────────┐ ┌────────┐ ┌────────────┐  │
│  │Qwen-VL │ │Qdrant  │ │Knowledge   │  │
│  │(视觉+) │ │(向量)  │ │YAML+Images │  │
│  └────────┘ └────────┘ └────────────┘  │
└─────────────────────────────────────────┘
```

详细架构请参见 [`docs/architecture.md`](docs/architecture.md)

## 项目结构

```
smart-shopping-guide-agent/
├── backend/              # FastAPI 后端服务（部署在 GB10）
├── frontend-console/     # 服务端 Console（演示者用，桌面 UI）
├── frontend-h5/          # 移动端 H5（顾客用，移动 UI）
├── frontend-app/         # Flutter 原生 App（Phase 2）
├── knowledge/            # 产品知识库
│   ├── products/         #   YAML 产品数据
│   ├── images/           #   产品图片库
│   └── schema.yaml       #   Schema 定义
├── deployment/           # 部署配置（1Panel/Docker/Helm）
└── docs/                 # 设计文档
    ├── prd.md            #   产品需求文档（PRD）
    ├── architecture.md   #   架构设计
    └── roadmap.md        #   路线图
```

## 文档导航

| 文档 | 内容 |
|------|------|
| **[`docs/prd.md`](docs/prd.md)** | **产品需求文档（PRD）— 项目核心** |
| [`docs/architecture.md`](docs/architecture.md) | 端到端架构设计 + 数据流 |
| [`docs/roadmap.md`](docs/roadmap.md) | 5 个阶段的详细路线图 |
| [`backend/README.md`](backend/README.md) | 后端服务说明 |
| [`frontend-console/README.md`](frontend-console/README.md) | 服务端 Console 说明 |
| [`frontend-h5/README.md`](frontend-h5/README.md) | 移动端 H5 说明 |
| [`knowledge/README.md`](knowledge/README.md) | 知识库结构与使用 |
| [`deployment/README.md`](deployment/README.md) | 部署方式 |

## 快速开始（开发）

### 后端服务

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 服务端 Console

```bash
cd frontend-console
npm install
npm run dev
# Console 在 http://localhost:5173 (开发模式)
```

### 移动端 H5

```bash
cd frontend-h5
npm install
npm run dev
# H5 在 http://localhost:5174 (开发模式)
# 手机扫码访问 http://<开发机 IP>:5174
```

### 一键部署（Docker）

```bash
docker build -t smart-guide-agent:0.1.0 .
docker run --gpus all -p 8080:8080 \
  -v $(pwd)/knowledge:/app/knowledge \
  -v $(pwd)/models:/app/models \
  smart-guide-agent:0.1.0
```

部署后：
- 服务端 Console: `http://<server-ip>:8080/`
- 移动端 H5: `http://<server-ip>:8080/m`

## 路线图

- [x] 项目初始化 + PRD 文档
- [ ] **Phase 1 - MVP H5 Demo（第 1 周）**
  - [ ] 后端 FastAPI + Qwen-VL 集成
  - [ ] 服务端 Console（含 QR Code 页面）
  - [ ] 移动端 H5（拍照 + 结果展示）
  - [ ] 3-5 个 SKU 知识库 + 图片库
  - [ ] Docker 一键部署
- [ ] **Phase 2 - 企业版（第 2-3 周）**：Flutter App + 1Panel 应用包
- [ ] **Phase 3 - 知识库扩展**：100+ SKU、ERP 集成、ROI 看板
- [ ] **Phase 4 - 高级功能**：语音对话、AR 叠加、多语言
- [ ] **Phase 5 - KWeaver Box 集成**：打包为 .kwapp 上架 AppHub

## 关于 KWeaver Box

KWeaver Box 是面向企业现场的边缘 AI 操作系统，以"算力盒子 + AppHub 平台 + 数字员工应用（.kwapp）"为核心形态。本项目作为 KWeaver Box 的首批标杆 .kwapp 应用，验证整个平台的端到端能力。

更多信息：[https://github.com/kweaver-ai/](https://github.com/kweaver-ai/)

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
