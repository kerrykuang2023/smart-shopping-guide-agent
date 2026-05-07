# Deployment

> **Demo 阶段策略**：直接 Docker 部署到 FusionXpark GB10。**不做 .kwapp 打包**（推迟到 Phase 5），**不做 1Panel app 包装**（推迟到 Phase 2-3 评估）。优先跑通场景，简化架构。

## 部署方式总览

| 阶段 | 部署方式 | 状态 |
|------|---------|------|
| **Demo（Phase 1）** | **Docker / docker-compose** ⭐ | 当前 |
| 客户 PoC（Phase 2-3） | docker-compose 多容器 + 简单运维脚本 | 计划 |
| 生产（Phase 5） | KWeaver Box AppHub + .kwapp（Helm Chart） | 远期 |

## 子目录

| 目录 | 内容 |
|-----|------|
| `docker/` | Docker / docker-compose 部署文件（**Demo 阶段使用**） |
| ~~`1panel/`~~ | ~~1Panel 应用包~~（已删除，Demo 不做） |
| `kwapp/` | `.kwapp` 打包规范（远期 KWeaver Box 集成） |

---

## 推荐部署方式：Docker Compose

### 在 FusionXpark GB10 上

```bash
# 1. 登录设备
ssh user@fusionxpark-ip

# 2. 克隆代码
git clone https://github.com/kerrykuang2023/smart-shopping-guide-agent.git
cd smart-shopping-guide-agent

# 3. 启动（首次启动会下载模型，约 5-10 分钟）
docker compose -f deployment/docker/docker-compose.yml up -d

# 4. 验证
curl http://localhost:8080/api/v1/health
# 应返回 {"status": "ok"}

# 5. 浏览器访问
# Console: http://<gb10-ip>:8080/
# Mobile H5: http://<gb10-ip>:8080/m
```

### 一键脚本

```bash
# 启动
./scripts/start.sh

# 停止
./scripts/stop.sh

# 查看日志
./scripts/logs.sh

# 预下载模型（首次部署前推荐执行）
./scripts/preload-models.sh
```

---

## 硬件要求

### 最低配置

| 资源 | 最低 | 推荐 |
|------|-----|------|
| GPU | 8GB VRAM | 16GB+ |
| 系统内存 | 16GB | 32GB+ |
| 存储 | 50GB | 100GB+ |
| 网络 | 局域网 100Mbps | 千兆 |

### 推荐设备

1. **FusionXpark GB10**（生产首选）：1 PFLOPS、128GB unified memory，跑 Qwen-VL 流畅，并发 50+
2. **NVIDIA RTX 4080/4090 工作站**：开发测试用，性能足够
3. **Jetson AGX Orin（64GB）**：边缘部署备选
4. **云 GPU（A100/H100）**：临时验证用

---

## 网络与安全

### Demo 阶段

- 服务监听 `0.0.0.0:8080`，**仅在局域网内访问**
- **无需 HTTPS**（局域网内）
- **无需用户认证**（演示简化）
- 演示模式默认开启，识别失败有兜底数据

### 生产阶段（Phase 2+）

- 启用 HTTPS（Let's Encrypt 或自签证书）
- Console 增加 JWT 登录
- 启用速率限制
- 增加审计日志

---

## 故障排查

### 容器启动失败

```bash
# 查看日志
docker compose logs smart-guide-agent

# 常见问题：
# 1. GPU 不可用：检查 nvidia-container-toolkit 是否安装
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# 2. 端口被占用
sudo lsof -i :8080
# 修改 docker-compose.yml 中的端口映射

# 3. 模型下载慢
# 编辑 .env，配置国内镜像：HF_ENDPOINT=https://hf-mirror.com
```

### 识别准确率低

1. 检查产品图片质量（光照、角度、清晰度）
2. 知识库 YAML 中产品描述是否充分
3. 在 Console 启用"演示模式"作为兜底

### 服务响应慢

1. `nvidia-smi` 检查 GPU 是否被占用
2. `docker stats` 检查容器资源使用
3. 如果是 Jetson 设备，考虑切换到 Qwen2.5-VL-3B 模型

---

## 未来演进

```
Demo 阶段：           docker compose up
                          ↓
客户 PoC 阶段：        docker compose + 简单监控
                          ↓
小规模产线阶段：      docker swarm 或 K3s
                          ↓
KWeaver Box 集成：    .kwapp 打包 → AppHub 一键安装 ← 远期目标
```

> 详细路线见 [`docs/roadmap.md`](../docs/roadmap.md)。
