# 🏔️ 越野智行 OffroadTrip

> 大模型智能体驱动的越野自驾游路线规划平台

结合多阶段 AI Agent 流水线、地图可视化、移动优先明亮风格，为越野自驾爱好者提供个性化路线规划。根据出发地、目的地、时间、车型和天气，生成包含特色景点、地方美食、历史故事、抖音视频链接的完整行程。

**在线体验**：https://offroad.guofeng.me — 填写出发地、目的地、天数，AI 在 1-2 分钟内生成完整越野路线，含逐日行程、景点特色、美食故事、历史典故、抖音视频链接。

## ✨ 核心特性

- 🤖 **多智能体编排** — 6 阶段 Agent 流水线（地理编码→天气→LLM规划→路况细化→内容丰富→组装），SSE 实时推送进度
- 🗺️ **地图可视化** — 3D 视角、按天分色路线、POI 自定义标记
- 🌿 **越野自然主题** — 轻度越野路线推荐，车型感知（SUV 可走非铺装路，轿车只走铺装路），天气影响越野决策
- 📱 **移动优先** — 底部抽屉日程、卡片式内容、明亮自然风格（绿/蓝/橙配色）
- 🍽️ **深度内容** — 景点特色说明（"为什么值得去"）、美食背后的故事、历史人物事件趣事
- 🎬 **抖音视频** — 为每个景点/美食/故事生成抖音搜索跳转链接
- 🌤️ **天气感知** — 结合出发时间天气，雨天降级越野路段，极端天气绕行建议
- 🔧 **大模型驱动** — 火山方舟 Agent Plan（`ark-code-latest`）为主，Cloudflare Workers AI 为免费兜底，双 key 自动主备切换
- ⏱️ **稳定的超时/重试设计** — 每个 LLM 调用单次尝试 + 硬超时，重试只在 Workflow step 层做一次，避免超时叠加导致流水线挂起（详见下文「稳定性设计」）

## 🏗️ 两套实现

本仓库包含**两套后端实现**，功能等价：

| | `workers/`（生产部署，推荐） | `backend/`（Python 参考实现） |
|---|---|---|
| 运行时 | Cloudflare Workers (TypeScript) | FastAPI (Python) |
| 长流水线 | Cloudflare Workflows（durable steps） | asyncio 异步生成器 |
| 进度推送 | Durable Object + SSE | 直接 SSE 流 |
| 数据库 | Cloudflare D1 (SQLite) | PostgreSQL / SQLite |
| 缓存 | Workers KV | 进程内内存 |
| 地图/地理编码 | Nominatim (OSM) + OSRM，免费无 key | 腾讯地图（需 key，有兜底） |
| 天气 | wttr.in，免费无 key | 和风天气（可选 key）+ wttr.in 兜底 |
| 图片 | picsum.photos，免费无 key | Unsplash（可选 key）+ picsum 兜底 |
| 部署形态 | 单 Worker（前端 Static Assets + API 同域） | Docker Compose（Nginx + FastAPI + Postgres） |

线上服务 https://offroad.guofeng.me 跑的是 `workers/` 版本，除 LLM 外全部使用免费服务，零外部 key 依赖。`backend/` 保留作为参考实现和 [`skill/`](#-使用-skill) 独立 CLI 的运行依赖。

## 🚀 快速开始

### 方式一：Cloudflare Workers（推荐）

```bash
cd workers
npm install

# 1. 创建 D1 数据库 + KV 命名空间，把返回的 id 填进 wrangler.toml
npx wrangler d1 create offroadtrip
npx wrangler kv namespace create GEO_CACHE

# 2. 应用数据库迁移
npx wrangler d1 migrations apply offroadtrip --remote

# 3. 配置 LLM（可选 —— 不配置则自动兜底到免费的 Cloudflare Workers AI）
# 火山方舟 Agent Plan 示例：model=ark-code-latest，
# base URL=https://ark.cn-beijing.volces.com/api/plan/v3（也可用任何 OpenAI 兼容网关）
npx wrangler secret put SILK_GATEWAY_KEY      # 主 key
npx wrangler secret put SILK_GATEWAY_KEY_2    # 可选：第二把 key，主 key 失败时自动切换

# 4. 构建前端并部署
cd ../frontend && npm install && npm run build
cd ../workers && npx wrangler deploy

# 5.（可选）绑定自定义域名
npx wrangler deploy   # 之后在 Cloudflare Dashboard 或 API 绑定 Workers 自定义域名
```

本地开发：`npx wrangler dev`（D1/KV 使用本地模拟，无需真实凭据）。

### 方式二：本地 Python + Vue（Docker 或裸机）

```bash
# 1. 克隆仓库
git clone https://github.com/suvlife/offroad-trip.git
cd offroad-trip

# 2. 配置后端环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入你的 API key（无 key 时各服务优雅降级）

# 3. 启动后端（使用 SQLite，无需 Docker）
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000 --env-file .env

# 4. 启动前端（新终端）
cd frontend
pnpm install
cp .env.example .env.development
pnpm dev
```

打开 **http://localhost:5173** 即可使用。

或者一键 Docker 部署：

```bash
cp backend/.env.example .env
# 编辑 .env 填入所有 key
docker-compose up -d
# 前端: http://localhost ｜ 后端: http://localhost:8000 ｜ API 文档: http://localhost:8000/docs
```

## 📁 项目结构

```
offroad-trip/
├── workers/                    # ★ Cloudflare Workers 后端（生产部署）
│   ├── src/
│   │   ├── index.ts            # Hono 路由 + 静态资源入口
│   │   ├── workflow.ts          # OffroadTripWorkflow：6 阶段 durable steps
│   │   ├── progress-do.ts       # ProgressCoordinator Durable Object（SSE 推送）
│   │   ├── pipeline.ts          # 6 阶段流水线逻辑 + 内容丰富 agent
│   │   ├── prompts.ts           # Prompt 模板
│   │   ├── db.ts                # D1 持久化
│   │   ├── types.ts             # 共享类型 + Env 绑定
│   │   └── services/            # geo(Nominatim) / routing(OSRM) / weather(wttr.in)
│   │                            # / images(picsum) / douyin / cost / llm(火山方舟+Workers AI)
│   ├── migrations/0001_init.sql # D1 schema（9 张表）
│   └── wrangler.toml
├── backend/                    # Python 参考实现（FastAPI）
│   ├── app/
│   │   ├── main.py             # 入口
│   │   ├── config.py           # 配置（火山方舟/腾讯地图/和风天气）
│   │   ├── database.py         # SQLAlchemy（PostgreSQL/SQLite 自动切换）
│   │   ├── models/route.py     # 9 张表（含越野/历史/抖音字段）
│   │   ├── schemas/route.py    # Pydantic 模型（前后端字段统一）
│   │   ├── routers/            # API 路由
│   │   ├── agents/             # 智能体编排层（orchestrator + planner + content + weather）
│   │   ├── services/           # 外部服务（LLM/腾讯地图/天气/费用/图片/抖音）
│   │   └── prompts/            # Prompt 模板
│   ├── tests/                  # pytest（cost/schemas/routes API/content agents/generate API）
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Vue3 前端（两套后端共用）
│   ├── src/
│   │   ├── views/              # HomeView / PlanningView(SSE进度) / RouteView(地图) / ShareView
│   │   ├── stores/route.js     # Pinia 状态管理
│   │   ├── utils/
│   │   │   ├── map.js          # MapLibre GL + 免费 OSM 瓦片（workers 版用）
│   │   │   ├── sse.js          # SSE 客户端（两步流：POST 启动 + GET 订阅进度）
│   │   │   └── ...
│   │   └── assets/main.css     # Tailwind + 明亮主题
│   ├── Dockerfile
│   └── nginx.conf
├── skill/                      # ZCode Skill（依赖 backend/，独立 CLI）
│   └── offroad-trip-planner/
│       ├── SKILL.md
│       ├── scripts/plan_offroad_trip.py
│       └── references/offroad-routes.md
├── docker-compose.yml
└── PLAN.md                     # Cloudflare 重构与部署的详细规划记录
```

## 🔌 API 端点

两套后端 API 形状基本一致，`workers/` 版的生成流程分两步（启动 + SSE 订阅），因为 Cloudflare Workflows 是异步任务模型：

| 方法 | 路径 | 说明 | workers/ | backend/ |
|------|------|------|:---:|:---:|
| POST | `/api/generate` | 启动路线生成 | 返回 `{instanceId}` | 直接 SSE 流 |
| GET | `/api/stream/:instanceId` | SSE 进度 + 最终路线 | ✅ | — |
| GET | `/api/routes` | 路线列表 | ✅ | ✅ |
| GET | `/api/routes/{id}` | 路线详情 | ✅ | ✅ |
| POST | `/api/routes/{id}/share` | 发布路线，生成分享链接 | ✅ | ✅ |
| DELETE | `/api/routes/{id}` | 删除路线 | ✅ | ✅ |
| GET | `/api/share/{share_id}` | 分享页数据（只读） | ✅ | ✅ |
| GET | `/api/weather?city=&days=` | 天气查询 | ✅ | ✅ |

## 🤖 智能体流水线

用户点击"开始规划路线"后，后端执行 6 阶段 Agent 流水线，进度实时推送到前端：

| 阶段 | 说明 | workers/ 数据源 | backend/ 数据源 |
|------|------|--------|--------|
| 1. 地理编码 | 出发地/目的地/沿途景点 → 坐标 | Nominatim（免费，KV 缓存） | 腾讯地图 WebService |
| 2. 天气查询 | 沿途城市逐日天气 → 越野决策 | wttr.in（免费） | 和风天气 / wttr.in |
| 3. LLM 规划 | 生成路线骨架（车型/天气感知） | 火山方舟 `ark-code-latest` | 火山方舟 glm-5.2 |
| 4. 路况细化 | 每段获取 polyline/里程/过路费 | OSRM（免费） | 腾讯地图路径规划 |
| 5. 内容丰富 | 景点特色/美食故事/历史典故（按天并行） | 火山方舟 | 火山方舟 |
| 6. 组装 | 图片/抖音链接/费用计算/落库 | picsum + D1 | Unsplash + PostgreSQL/SQLite |

**生成内容示例**（北京→承德 2 天，`workers/` 线上实测）：
- 📌 路线标题："京承秘境：燕山山脉避暑寻幽之旅"
- 🎯 特色景点：白河湾自然风景区、金山岭长城、磬锤峰国家森林公园、僧冠峰
- 🍽️ 地方美食：姚记炒肝店（含京承饮食渊源故事）
- 📖 历史故事：磬锤峰"康熙赐名"典故
- 💰 费用估算：¥1972（含油费/过路费/住宿/餐饮/门票明细）
- ⏱️ 全流程实测约 2 分钟完成

## 🛡️ 稳定性设计：超时与重试

`workers/` 版的 LLM 调用遵循一条硬规则：**重试只在一层发生**。

- `services/llm.ts` 对每把网关 key 只发起**一次** HTTP 请求，90 秒硬超时（实测火山方舟完整规划请求约 50 秒返回），不做内部重试；失败就换下一把 key，两把都失败则兜底到免费的 Cloudflare Workers AI。
- 真正的重试逻辑放在 `workflow.ts` 的 `step.do(...)` 显式配置里（`planning` 步骤：4 分钟超时、最多 2 次重试；`enrichment` 同理）。

这么设计是因为踩过一个坑：如果内部重试（3次 × 5分钟超时）和 Workflow 层的默认重试（10分钟超时、近乎无限重试）同时存在，两者是**乘法叠加**而不是加法——一次稍慢的调用会被 Workflow 默认超时中途强杀，然后整个步骤重跑，又撞上同样的问题，如此循环。线上曾因此在"AI正在规划越野路线...30%"卡住 8 小时以上。现在两层只有一层负责重试，最坏耗时可预测、有边界。

## 🛠️ 技术栈

| 层 | `workers/`（生产） | `backend/`（参考实现） |
|---|---|---|
| 运行时/框架 | Cloudflare Workers + Hono | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| 长流水线 | Cloudflare Workflows | asyncio |
| 进度推送 | Durable Objects + SSE | SSE (StreamingResponse) |
| 数据库 | Cloudflare D1 | PostgreSQL / SQLite |
| 缓存 | Workers KV | 无（进程内） |
| LLM | 火山方舟 Agent Plan + Cloudflare Workers AI 兜底 | 火山方舟 Agent Plan |
| 静态托管 | Workers Static Assets | Nginx (Docker) |
| 前端 | Vue3 + Vite 5 + Pinia + TailwindCSS 3 + MapLibre GL | 同左 + 腾讯地图 JS API GL |

## 🎯 使用 Skill

本仓库内置 ZCode Skill，依赖 `backend/`，可独立运行路线规划（无需启动 Web 服务）：

```bash
# 安装 skill（链接到 ZCode skills 目录）
ln -s $(pwd)/skill/offroad-trip-planner ~/.zcode/skills/offroad-trip-planner

# 独立运行规划脚本
python skill/offroad-trip-planner/scripts/plan_offroad_trip.py \
  --from 北京 --to 沈阳 --days 3 --vehicle SUV --date 2026-07-10
```

需要环境变量：`SILK_GATEWAY_URL`、`SILK_GATEWAY_KEY`、`QQ_MAP_KEY`

## 🧪 测试

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -v
```

覆盖费用引擎、Pydantic schema 校验、路线 CRUD API、内容丰富 agent 的按天分组逻辑、生成 API 的 DB id 回传逻辑。

## 📄 License

MIT
