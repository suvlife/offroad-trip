# 🏔️ 越野智行 OffroadTrip

> 大模型智能体驱动的越野自驾游路线规划平台

结合多阶段 AI Agent 流水线、腾讯地图可视化、移动优先明亮风格，为越野自驾爱好者提供个性化路线规划。根据出发地、目的地、时间、车型和天气，生成包含特色景点、地方美食、历史故事、抖音视频链接的完整行程。

## ✨ 核心特性

- 🤖 **多智能体编排** - 6 阶段 Agent 流水线（地理编码→天气→路线规划→路况细化→内容丰富→组装），SSE 实时推送进度
- 🗺️ **腾讯地图可视化** - 3D 视角、按天分色路线、POI 标记、卫星图层
- 🌿 **越野自然主题** - 轻度越野路线推荐，车型感知（SUV 可走非铺装路，轿车只走铺装路），天气影响越野决策
- 📱 **移动优先** - 底部抽屉日程、卡片式内容、明亮自然风格
- 🍽️ **深度内容** - 景点特色说明、美食背后的故事、历史人物事件趣事
- 🎬 **抖音视频** - 为每个景点/美食生成抖音搜索跳转链接
- 🌤️ **天气感知** - 结合出发时间天气，雨天降级越野路段，极端天气绕行建议

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────┐
│                   前端 (Vue3 + Tailwind)              │
│  HomeView → PlanningView(SSE进度) → RouteView(地图)   │
└──────────────────────┬──────────────────────────────┘
                       │ SSE (fetch stream)
┌──────────────────────▼──────────────────────────────┐
│              后端 (FastAPI)                           │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │          Orchestrator (6阶段编排)             │    │
│  │                                              │    │
│  │  1.地理编码 → 2.天气 → 3.LLM规划             │    │
│  │  → 4.路况细化 → 5.内容丰富 → 6.组装          │    │
│  └──────┬──────────┬──────────┬────────────────┘    │
│         │          │          │                      │
│    ┌────▼───┐ ┌────▼───┐ ┌────▼────┐                │
│    │腾讯地图│ │和风天气│ │silk-gw  │                │
│    │  API   │ │  API   │ │ (LLM)  │                │
│    └────────┘ └────────┘ └─────────┘                │
│         │          │          │                      │
│    ┌────▼──────────▼──────────▼────┐                │
│    │     PostgreSQL / SQLite        │                │
│    └────────────────────────────────┘                │
└─────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 前置条件

| Key | 用途 | 获取 | 免费 |
|-----|------|------|------|
| `SILK_GATEWAY_URL` + `KEY` | LLM 接入 | 你的 silk-gateway | 自有 |
| `QQ_MAP_KEY` | 腾讯地图路线/POI | [lbs.qq.com](https://lbs.qq.com) | ✅ |
| `QWEATHER_KEY` | 和风天气 | [dev.qweather.com](https://dev.qweather.com) | ✅ |
| `UNSPLASH_KEY` | 景点照片 | [unsplash.com/developers](https://unsplash.com/developers) | ✅ |

> 无 key 时各服务有优雅降级（mock 数据/占位图），不阻塞开发。

### 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/suvlife/offroad-trip.git
cd offroad-trip

# 2. 配置后端环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入你的 API key

# 3. 启动后端 (使用 SQLite, 无需 Docker)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. 启动前端 (新终端)
cd frontend
pnpm install
cp .env.example .env.development  # 腾讯地图 key 已预填
pnpm dev
```

打开 http://localhost:5173 即可使用。

### Docker 部署

```bash
# 配置环境变量
cp backend/.env.example .env
# 编辑 .env 填入所有 key

# 一键启动 (PostgreSQL + 后端 + 前端)
docker-compose up -d

# 前端: http://localhost
# 后端: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

## 📁 项目结构

```
offroad-trip/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py             # 入口
│   │   ├── config.py           # 配置 (silk-gateway/腾讯地图/和风天气)
│   │   ├── database.py         # SQLAlchemy (PostgreSQL/SQLite 自动切换)
│   │   ├── models/route.py     # 9 张表 (含越野/历史/抖音字段)
│   │   ├── schemas/route.py    # Pydantic 模型 (前后端字段统一)
│   │   ├── routers/            # API 路由 (generate SSE / routes CRUD / weather)
│   │   ├── agents/             # ★ 智能体编排层
│   │   │   ├── orchestrator.py # 6 阶段流水线 + SSE
│   │   │   ├── planner_agent.py# 路线规划 (越野/自然主题)
│   │   │   ├── content_agents.py# 景点/美食/历史丰富
│   │   │   └── weather_agent.py# 天气决策
│   │   ├── services/           # 外部服务
│   │   │   ├── llm_service.py  # silk-gateway 接入
│   │   │   ├── qqmap_service.py# 腾讯地图 (地理编码/路径/POI)
│   │   │   ├── weather_service.py
│   │   │   ├── cost_service.py # 费用引擎
│   │   │   ├── image_service.py
│   │   │   └── douyin_service.py
│   │   └── prompts/            # Prompt 模板
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Vue3 前端
│   ├── src/
│   │   ├── views/              # 4 页面
│   │   ├── components/         # 地图/日程/卡片组件
│   │   ├── stores/route.js     # Pinia 状态
│   │   ├── utils/              # 腾讯地图/SSE/API
│   │   └── assets/main.css     # Tailwind + 明亮主题
│   ├── Dockerfile
│   └── nginx.conf
├── skill/                      # ZCode Skill
│   └── offroad-trip-planner/
│       ├── SKILL.md
│       ├── scripts/            # 独立规划脚本
│       └── references/         # 越野知识库
└── docker-compose.yml
```

## 🔌 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/generate` | 生成路线 (SSE 流式) |
| GET | `/api/routes` | 路线列表 |
| GET | `/api/routes/{id}` | 路线详情 |
| POST | `/api/routes/{id}/share` | 生成分享链接 |
| GET | `/api/share/{share_id}` | 分享页数据 |
| GET | `/api/weather?city=&days=` | 天气查询 |
| GET | `/api/cities?q=` | 城市搜索 |

## 🎯 使用 Skill

本仓库内置 ZCode Skill，可独立运行路线规划：

```bash
# 安装 skill (链接到 ZCode skills 目录)
ln -s $(pwd)/skill/offroad-trip-planner ~/.zcode/skills/offroad-trip-planner

# 独立运行规划脚本
python skill/offroad-trip-planner/scripts/plan_offroad_trip.py \
  --from 北京 --to 漠河 --days 7 --vehicle SUV --date 2026-07-08
```

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic v2 + httpx |
| LLM | silk-gateway (Cloudflare Workers, OpenAI 兼容, DeepSeek/豆包/Kimi) |
| 地图 | 腾讯位置服务 (WebService API + JS API GL) |
| 天气 | 和风天气 (QWeather) + wttr.in 兜底 |
| 前端 | Vue3 + Vite + Pinia + TailwindCSS |
| 部署 | Docker Compose (PostgreSQL + FastAPI + nginx) |

## 📄 License

MIT
