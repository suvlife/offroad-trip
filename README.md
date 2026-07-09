# 🏔️ 越野智行 OffroadTrip

> 大模型智能体驱动的越野自驾游路线规划平台

结合多阶段 AI Agent 流水线、腾讯地图可视化、移动优先明亮风格，为越野自驾爱好者提供个性化路线规划。根据出发地、目的地、时间、车型和天气，生成包含特色景点、地方美食、历史故事、抖音视频链接的完整行程。

**在线演示**：填写出发地、目的地、天数，AI 在 2-3 分钟内生成完整越野路线，含逐日行程、景点特色、美食故事、历史典故、抖音视频链接。

## ✨ 核心特性

- 🤖 **多智能体编排** — 6 阶段 Agent 流水线（地理编码→天气→LLM规划→路况细化→内容丰富→组装），SSE 实时推送进度
- 🗺️ **腾讯地图可视化** — JS API GL 3D 视角、按天分色路线、POI 自定义标记、卫星图层
- 🌿 **越野自然主题** — 轻度越野路线推荐，车型感知（SUV 可走非铺装路，轿车只走铺装路），天气影响越野决策
- 📱 **移动优先** — 底部抽屉日程、卡片式内容、明亮自然风格（绿/蓝/橙配色）
- 🍽️ **深度内容** — 景点特色说明（"为什么值得去"）、美食背后的故事、历史人物事件趣事
- 🎬 **抖音视频** — 为每个景点/美食/故事生成抖音搜索跳转链接
- 🌤️ **天气感知** — 结合出发时间天气，雨天降级越野路段，极端天气绕行建议
- 🔧 **大模型 + Skill** — 火山方舟 Agent Plan glm-5.2 驱动，内置 ZCode Skill 可独立运行

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────┐
│             前端 (Vue3 + TailwindCSS)                │
│  HomeView → PlanningView(SSE进度) → RouteView(地图)   │
└──────────────────────┬──────────────────────────────┘
                       │ SSE (fetch stream)
┌──────────────────────▼──────────────────────────────┐
│              后端 (FastAPI)                           │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │          Orchestrator (6阶段编排)             │    │
│  │                                              │    │
│  │  1.地理编码 → 2.天气 → 3.LLM规划              │    │
│  │  → 4.路况细化 → 5.内容丰富 → 6.组装           │    │
│  └──────┬──────────┬──────────┬────────────────┘    │
│         │          │          │                      │
│    ┌────▼───┐ ┌────▼───┐ ┌────▼────────┐           │
│    │腾讯地图│ │和风天气│ │火山方舟     │           │
│    │  API   │ │  API   │ │ glm-5.2 LLM│           │
│    └────────┘ └────────┘ └─────────────┘           │
│         │          │          │                      │
│    ┌────▼──────────▼──────────▼────┐                │
│    │     PostgreSQL / SQLite        │                │
│    └────────────────────────────────┘                │
└─────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 前置条件

| Key | 用途 | 获取方式 | 免费 |
|-----|------|---------|------|
| `SILK_GATEWAY_URL` + `KEY` | LLM 接入（火山方舟） | [console.volcengine.com/ark](https://console.volcengine.com/ark) | 按量付费 |
| `QQ_MAP_KEY` | 腾讯地图路线/POI/地理编码 | [lbs.qq.com](https://lbs.qq.com) | ✅ 个人免费 |
| `QWEATHER_KEY` | 和风天气（可选） | [dev.qweather.com](https://dev.qweather.com) | ✅ 1000次/天 |
| `UNSPLASH_KEY` | 景点/美食照片（可选） | [unsplash.com/developers](https://unsplash.com/developers) | ✅ 50次/小时 |

> 无 key 时各服务有优雅降级（mock 数据/占位图/wttr.in 兜底天气），不阻塞开发。

### 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/suvlife/offroad-trip.git
cd offroad-trip

# 2. 配置后端环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入你的 API key

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

### Docker 部署

```bash
# 配置环境变量
cp backend/.env.example .env
# 编辑 .env 填入所有 key

# 一键启动（PostgreSQL + 后端 + 前端）
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
│   │   ├── config.py           # 配置（火山方舟/腾讯地图/和风天气）
│   │   ├── database.py         # SQLAlchemy（PostgreSQL/SQLite 自动切换）
│   │   ├── models/route.py     # 9 张表（含越野/历史/抖音字段）
│   │   ├── schemas/route.py    # Pydantic 模型（前后端字段统一）
│   │   ├── routers/            # API 路由
│   │   │   ├── generate.py     # POST /api/generate（SSE 流式）
│   │   │   ├── routes.py       # 路线 CRUD + 分享
│   │   │   └── weather.py      # 天气 + 城市搜索
│   │   ├── agents/             # ★ 智能体编排层
│   │   │   ├── orchestrator.py # 6 阶段流水线 + SSE 事件
│   │   │   ├── planner_agent.py# 路线规划（越野/自然主题）
│   │   │   ├── content_agents.py# 景点/美食/历史丰富（并行）
│   │   │   └── weather_agent.py# 天气决策
│   │   ├── services/           # 外部服务
│   │   │   ├── llm_service.py  # 火山方舟接入（重试+推理模型支持）
│   │   │   ├── qqmap_service.py# 腾讯地图（地理编码/路径/POI + polyline解压）
│   │   │   ├── weather_service.py
│   │   │   ├── cost_service.py # 费用引擎
│   │   │   ├── image_service.py# Unsplash 图片
│   │   │   └── douyin_service.py# 抖音搜索链接生成
│   │   └── prompts/            # Prompt 模板
│   │       ├── planner.py      # 越野路线规划
│   │       └── content.py      # 景点/美食/历史
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Vue3 前端
│   ├── src/
│   │   ├── views/              # 4 个页面
│   │   │   ├── HomeView.vue    # 输入表单
│   │   │   ├── PlanningView.vue# SSE 进度可视化
│   │   │   ├── RouteView.vue   # 地图 + 底部抽屉日程
│   │   │   └── ShareView.vue   # 分享页
│   │   ├── stores/route.js     # Pinia 状态管理
│   │   ├── utils/
│   │   │   ├── qqmap.js        # 腾讯地图 GL（3D/路线/标记）
│   │   │   ├── sse.js          # SSE 客户端（大JSON分片处理）
│   │   │   └── ...
│   │   └── assets/main.css     # Tailwind + 明亮主题
│   ├── Dockerfile
│   └── nginx.conf
├── skill/                      # ZCode Skill
│   └── offroad-trip-planner/
│       ├── SKILL.md            # 触发词 + 使用说明
│       ├── scripts/            # 独立规划脚本（可脱离 Web 运行）
│       └── references/         # 越野路线知识库
├── docker-compose.yml
└── README.md
```

## 🔌 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/generate` | 生成路线（SSE 流式，返回 6 阶段进度 + 最终路线） |
| GET | `/api/routes` | 路线列表 |
| GET | `/api/routes/{id}` | 路线详情（含日程/景点/美食/故事/抖音链接） |
| POST | `/api/routes/{id}/share` | 发布路线，生成分享链接 |
| GET | `/api/share/{share_id}` | 分享页数据（只读） |
| GET | `/api/weather?city=&days=` | 天气查询 |
| GET | `/api/cities?q=` | 城市搜索（腾讯地图自动补全） |

## 🤖 智能体流水线

用户点击"开始规划路线"后，后端执行 6 阶段 Agent 流水线，通过 SSE 实时推送进度：

| 阶段 | 说明 | 数据源 |
|------|------|--------|
| 1. 地理编码 | 出发地/目的地 → 坐标 | 腾讯地图 WebService |
| 2. 天气查询 | 沿途城市逐日天气 → 越野决策 | 和风天气 / wttr.in |
| 3. LLM 规划 | 生成路线骨架（车型/天气感知） | 火山方舟 glm-5.2 |
| 4. 路况细化 | 每段获取 polyline/里程/过路费 | 腾讯地图路径规划 |
| 5. 内容丰富 | 景点特色/美食故事/历史典故（并行） | 火山方舟 glm-5.2 |
| 6. 组装 | 图片/抖音链接/费用计算/落库 | Unsplash + 费用引擎 |

**生成内容示例**（北京→沈阳 3 天）：
- 📌 路线标题："燕山辽河穿越之旅：从帝都到盛京的山野古道"
- 🎯 特色景点：草原天路、独石口长城、辽河源国家森林公园、牛河梁红山文化遗址、医巫闾山、沈阳故宫
- 🍽️ 地方美食：凌源豆腐脑、蒙古贞馅饼（含背后的故事）
- 📖 历史故事：皇太极与海兰珠、耶律倍望海堂藏书、努尔哈赤迁都沈阳
- 🎬 抖音链接：每个景点/美食/故事都有对应的抖音搜索跳转链接

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic v2 + httpx |
| LLM | 火山方舟 Agent Plan（glm-5.2，1M 上下文，推理模型） |
| 地图 | 腾讯位置服务（WebService API + JS API GL 3D） |
| 天气 | 和风天气（QWeather）+ wttr.in 兜底 |
| 图片 | Unsplash + Picsum 占位图 |
| 前端 | Vue3 + Vite 5 + Pinia + TailwindCSS 3 |
| 部署 | Docker Compose（PostgreSQL + FastAPI + nginx） |
| Skill | ZCode Skill（可独立运行的路线规划脚本） |

## 🎯 使用 Skill

本仓库内置 ZCode Skill，可独立运行路线规划（无需启动 Web 服务）：

```bash
# 安装 skill（链接到 ZCode skills 目录）
ln -s $(pwd)/skill/offroad-trip-planner ~/.zcode/skills/offroad-trip-planner

# 独立运行规划脚本
python skill/offroad-trip-planner/scripts/plan_offroad_trip.py \
  --from 北京 --to 沈阳 --days 3 --vehicle SUV --date 2026-07-10
```

需要环境变量：`SILK_GATEWAY_URL`、`SILK_GATEWAY_KEY`、`QQ_MAP_KEY`

## 📄 License

MIT
