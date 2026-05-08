# Demo Preparation Checklist

A practical pre-demo checklist for the Smart Shopping Guide Agent demo on FusionXpark GB10.

---

## 1. Physical Props (5 Signing Pens)

Pack a small zipper pouch with these 5 pens. Total cost ~¥80 if purchased fresh; most offices have 3-4 of these already.

| ✅ | Item | Where to get | Notes |
|---|------|-------------|-------|
| ☐ | 晨光优品 K35 中性笔（黑色 0.5mm） | 任意文具店 / 京东 ¥2.5 | 国民款，最容易找到 |
| ☐ | 得力 S01 中性笔（黑色 0.5mm） | 办公室抽屉 / 京东 ¥3 | 商务黑色磨砂质感 |
| ☐ | PILOT 百乐 G2 中性笔（黑色 0.7mm） | 京东 / 文具店 ¥18 | 透明笔身识别度高 |
| ☐ | 英雄 359 钢笔（F 尖） | 京东 / 礼品店 ¥45 | 最有故事的产品 |
| ☐ | Stabilo Boss 荧光笔（黄色） | 京东 / 文具店 ¥12 | 颜色鲜明，演示效果好 |

**总成本**：约 ¥80 / **最少需要**：3 支（K35 + G2 + 任一其他）

---

## 2. Hardware

| ✅ | Item | Verification |
|---|------|--------------|
| ☐ | FusionXpark GB10 已就绪 | `ssh root@<gb10-ip>` 可登录 |
| ☐ | 笔记本电脑（演示者） | HDMI / Type-C → 投影 |
| ☐ | 演示者手机（备份扫码） | iOS + Android 各一部 |
| ☐ | 网线 / WiFi | GB10 与笔记本同网段 |
| ☐ | 演示者手机 4G 热点 | 网络故障时 Plan B |
| ☐ | HDMI 线 / 转接头 | 投屏到客户大屏 |

---

## 3. Software Pre-Flight (T-30 分钟)

```bash
# 1. SSH 到 FusionXpark GB10
ssh root@<gb10-ip>

# 2. 启动服务
cd /opt/smart-shopping-guide
docker compose up -d

# 3. 等待模型预加载（~3 分钟）
docker compose logs -f backend | grep "Model loaded"

# 4. 验证健康检查
curl http://localhost:8080/api/v1/health
# 期望返回：{"status":"healthy","models":["qwen2.5-vl-7b"]}

# 5. 验证 5 个 SKU 已加载
curl http://localhost:8080/api/v1/products | jq '. | length'
# 期望返回：5

# 6. 浏览器访问 Console
open http://<gb10-ip>:8080
```

---

## 4. Demo Rehearsal (T-15 分钟)

| ✅ | Step | Expected Result |
|---|------|----------------|
| ☐ | 笔记本浏览器打开 Console 主页 | Dashboard 显示，5 个 SKU 已加载 |
| ☐ | 进入 QR Code 全屏页 | QR Code 清晰可扫 |
| ☐ | 演示者手机扫码 | H5 页面在 1 秒内打开，定位到拍照页 |
| ☐ | 用手机拍 PILOT G2 | 1.5 秒内识别成功，主图正确显示 |
| ☐ | 测试追问"和晨光 K35 比怎么样" | 流式回答，3 秒内开始输出 |
| ☐ | 切回 Console 看调用日志 | 刚才的拍照记录显示 |

---

## 5. Demo Script Cheat Sheet

### 5.1 黄金推荐 SKU：PILOT 百乐 G2

**为什么选 G2 做主演示**：
- 透明笔身识别度极高（vs 全黑笔身的 S01）
- 故事最丰富：日本品牌 / 啫喱墨水专利 / 全球 10 亿支
- 价格中等（¥18），既不便宜到没故事，也不贵到客户觉得离自己远
- 关联推荐丰富（笔芯、套装、Moleskine 笔记本）
- 竞品对比戏剧性强（vs 晨光 K35 价差 7 倍）

### 5.2 五分钟脚本要点

```
00:00-00:35  Console 主页 + QR Code 介绍
00:35-00:50  客户扫码打开 H5
00:50-01:10  客户拍 PILOT G2
01:10-01:30  AI 讲解展开（带配图）
01:30-02:30  追问"和晨光 K35 对比"
02:30-03:00  展示关联推荐 + 竞品对比
03:00-03:30  切回 Console 看调用日志
03:30-04:00  讲 KWeaver Box 大故事
04:00-05:00  Q&A
```

### 5.3 客户问题应对

| 客户问 | 标准应答 |
|--------|---------|
| "识别准确率多少？" | "我们这 5 个 SKU 实测 ≥80%，扩到客户实际 SKU 库会再训练" |
| "支持多少个 SKU？" | "GB10 单机 1000+ SKU 无压力，KWeaver DIP 云端可支持百万级" |
| "数据安全吗？" | "完全本地推理，数据不出您的内网" |
| "网络不通能用吗？" | "可以，所有模型都在边缘盒子上，断网也能跑" |
| "多少钱？" | "盒子 + 软件许可，POC 阶段免费共创" |

---

## 6. Backup Plan

| 故障 | Plan B |
|------|--------|
| 客户 WiFi 不让笔记本 / GB10 同网段 | 手机开热点，重新部署 docker compose |
| 客户手机扫码失败 | 借用演示者备用手机 |
| 笔实物忘带 | 用客户办公室任意一支签字笔（识别失败用 demo mode 兜底） |
| GPU 服务挂了 | 重启 `docker compose restart backend`，30 秒恢复 |
| 模型识别错误 | demo mode 已开启，自动返回 mock 数据 |
| 投屏无法连接 | 围着笔记本看，依然可演示 |

---

## 7. Post-Demo

| ✅ | Action |
|---|--------|
| ☐ | 导出本次演示的调用日志（`/api/v1/logs?session=demo-yyyymmdd`） |
| ☐ | 客户感兴趣的 SKU / 行业记录到 CRM |
| ☐ | 收集客户对 H5 vs 原生 App 的偏好 |
| ☐ | 跟进：是否进入 PoC 阶段共创 |

---

## 8. Demo Day Pack List

打包一个小手提包，里面装：

- [ ] 5 支签字笔（拉链袋）
- [ ] 演示者笔记本电脑 + 充电器
- [ ] HDMI 线 + Type-C 转接头
- [ ] 网线 1 根（应急）
- [ ] 备用 Android 手机
- [ ] 名片
- [ ] PRD 打印版（应客户深问技术）
- [ ] 架构图打印版（应客户问"这个怎么部署的"）

---

**最后提醒**：
- 演示前 30 分钟到场，预热模型
- 演示中保持轻松，遇到 Bug 笑着说"演示模式启动" 
- 演示后 24 小时内必须发跟进邮件
