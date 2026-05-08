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
- **语音交互**：按住说话，AI 语音回复
- **完全离线**：部署在边缘端（FusionXpark/DGX Spark），数据不出店

## 快速开始

### 方式一：Docker 一键部署（推荐）

**环境要求**：Docker + Docker Compose

```bash
# 克隆项目
git clone https://github.com/kerrykuang2023/smart-shopping-guide-agent.git
cd smart-shopping-guide-agent

# 启动服务（开发模式，使用 Mock 数据）
docker compose -f deployment/docker/docker-compose.yml up -d

# 或使用便捷脚本
./scripts/start.sh
```

**部署后访问**：
- **服务端 Console**: http://localhost:8080/
- **移动端 H5**: http://localhost:8080/m（手机扫码访问）

### 方式二：本地开发环境

**后端服务（Python）**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

**前端 Console（Vue3）**

```bash
cd frontend-console
npm install
npm run dev
# 访问 http://localhost:5173
```

**前端 H5（Vue3）**

```bash
cd frontend-h5
npm install
npm run dev
# 访问 http://localhost:5174
```

## 如何使用

### 第一步：访问管理后台

浏览器打开 `http://<服务器IP>:8080/`

- 查看产品列表和状态
- 配置外部 AI 模型（VLM/LLM/TTS/ASR）
- 生成移动端二维码

### 第二步：手机扫码体验

1. 点击"移动端入口"查看二维码
2. 用手机扫码进入 H5 页面
3. **拍照识别**：对准产品点击大圆按钮
4. **或选择相册**：点击相册图标从手机选图

### 第三步：与 AI 互动

- **自动讲解**：识别后 AI 自动语音播报产品卖点
- **语音追问**：按住麦克风按钮说话提问
- **文字追问**：输入框输入问题
- **关联推荐**：查看搭配产品和竞品对比

### 离线语音（可选）

如需使用本地语音识别和合成（无需网络）：

```bash
# 进入容器下载语音模型
docker exec -it smart-guide-agent bash
python scripts/download_sherpa_models.py --all

# 退出并重启
docker restart smart-guide-agent
```

## 演示流程

```
1. 演示者打开笔记本浏览器 → http://server:8080
2. 服务端 Console 显示 Dashboard / 知识库管理 / 模型配置
3. 切换到"移动端入口"页面 → 大屏显示 QR Code
4. 观众/客户用手机扫码 → 进入移动端 H5
5. 手机拍摄展台产品 → 后端 AI 识别
6. 手机展示富图片产品卡片 + 关联推荐 + 竞品对比
7. 顾客追问 → AI 流式回答
```

完整演示脚本见 [`docs/prd.md`](docs/prd.md#12-演示流程设计)

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
│  │Qwen-VL │ │Sherpa  │ │Knowledge   │  │
│  │(视觉+) │ │(语音)  │ │YAML+Images │  │
│  └────────┘ └────────┘ └────────────┘  │
└─────────────────────────────────────────┘
```

详细架构请参见 [`docs/architecture.md`](docs/architecture.md)

## 项目结构

```
smart-shopping-guide-agent/
├── backend/              # FastAPI 后端服务
│   ├── app/              #   应用代码
│   ├── static/           #   静态文件
│   └── tests/            #   测试文件
├── frontend-console/     # 服务端 Console（Vue3）
├── frontend-h5/          # 移动端 H5（Vue3）
├── knowledge/            # 产品知识库
│   ├── products/         #   YAML 产品数据
│   └── images/           #   产品图片库
├── deployment/           # 部署配置（Docker）
├── scripts/              # 辅助脚本
└── docs/                 # 设计文档
    ├── prd.md            #   产品需求文档
    └── architecture.md   #   架构设计
```

## 文档导航

| 文档 | 内容 |
|------|------|
| **[`docs/prd.md`](docs/prd.md)** | **产品需求文档（PRD）— 项目核心** |
| [`docs/architecture.md`](docs/architecture.md) | 端到端架构设计 + 数据流 |
| [`backend/README.md`](backend/README.md) | 后端服务说明 |
| [`frontend-console/README.md`](frontend-console/README.md) | 服务端 Console 说明 |
| [`frontend-h5/README.md`](frontend-h5/README.md) | 移动端 H5 说明 |
| [`knowledge/README.md`](knowledge/README.md) | 知识库结构与使用 |
| [`deployment/README.md`](deployment/README.md) | 部署方式 |

## 关于 KWeaver Box

KWeaver Box 是面向企业现场的边缘 AI 操作系统，以"算力盒子 + AppHub 平台 + 数字员工应用（.kwapp）"为核心形态。本项目作为 KWeaver Box 的首批标杆 .kwapp 应用，验证整个平台的端到端能力。

更多信息：[https://github.com/kweaver-ai/](https://github.com/kweaver-ai/)

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
