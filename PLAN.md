# 越野智行 · Cloudflare 化重构与部署规划

> 本文件是根据「① 修复现存问题 ② 部署到 Cloudflare 并用足 CF 产品能力 ③ 除 LLM 外全部免费、无需额外 key」三项要求，对 OffroadTrip 的重新梳理。

## 0. 已确认的架构决策

| 维度 | 决策 | 说明 |
|------|------|------|
| 后端 | **全量重写为 Cloudflare Workers (TypeScript)** | 弃用 Python/FastAPI 运行时，改用 CF 原生运行时 |
| 长流水线 | **Cloudflare Workflows** | 6 阶段做成 durable steps，每步可重试、可长跑 |
| 进度推送 | **Durable Object** 支撑 SSE | 任务进度 pub/sub，前端 SSE 订阅 |
| 数据库 | **Cloudflare D1** (SQLite) | 现有模型已支持 SQLite，schema 平滑迁移 |
| 缓存 | **Workers KV** | geocode 结果缓存（替代进程内缓存，Worker 无常驻内存） |
| 前端 | **Cloudflare Pages** + 自定义域名 | Vue3 静态托管，绑 Zone 对应域名 |
| LLM | 用户提供 key（火山方舟 glm-5.2） | 存为 Worker Secret，唯一需要的 key |

## 1. req 3 的直接后果：地图/天气/图片全部去 key 化

代码原本围绕**腾讯地图（需 key）**构建。要做到「除 LLM 外无需任何 key」，必须替换为无 key 的开放服务：

| 能力 | 原方案(需key) | 新方案(无key/免费) | 备注 |
|------|--------------|-------------------|------|
| 地理编码 | 腾讯 WebService | **Nominatim (OSM)** + 内置城市坐标表兜底 | 已有 45 城表做离线兜底，可扩充 |
| 路径规划/polyline | 腾讯方向 API | **OSRM 公共服务** + 大圆航线兜底 | 拿真实道路 polyline |
| 地图显示 | 腾讯 JS GL(需key) | **MapLibre GL JS** + 免费 OSM 栅格瓦片 | 前端换库，无 key |
| 天气 | 和风天气(需key) | **wttr.in** | 代码已有此兜底，几乎零改动 |
| 图片 | Unsplash(需key) | **picsum.photos** 占位图 | 代码已有此兜底 |
| 抖音链接 | 无 API | 纯字符串生成 | 不变 |

**关键工程点 — 坐标系统一为 WGS-84**：腾讯用 GCJ-02，OSM/Nominatim/OSRM/OSM 瓦片全用 WGS-84。弃用腾讯后，全链路统一 WGS-84，点位与瓦片天然对齐，规避了中国区最头疼的 ~500m 偏移问题。

**取舍提示**：OSM 系在中国的地名覆盖/路网精度弱于腾讯，Nominatim/OSRM 公共服务器有速率限制、非生产级。若你愿意为地图破例申请一个**免费**腾讯 key，中国区精度会明显更好。默认按你的「无 key」要求走 OSM 系；如需破例请告知。

## 2. req 1：现存问题修复清单（本轮已改）

| # | 问题 | 文件 | 状态 |
|---|------|------|------|
| 1 | 生成后路线拿不到 DB id（落库在最终事件之后） | `routers/generate.py` | ✅ 已改：拦截最终事件→先落库→注入 id/share_id→再转发 |
| 2 | 内容丰富阶段 POI 被重复归城（一天多段→重复 LLM 调用+竞态） | `agents/content_agents.py` | ✅ 已改：按天分组，每 POI 只丰富一次 |
| 3 | POI 坐标从不落库（地图标记退化到城市中心） | `agents/orchestrator.py` | ✅ 已改：stage4 对 POI geocode 补坐标 |
| 4 | 天气逐日建议只是整段 blob 复制到每天 | `agents/orchestrator.py` + `weather_agent.py` | ✅ 已改：按当天终点城市生成 per-day 建议 |
| 5 | stage4 同城反复串行 geocode，无缓存 | `services/qqmap_service.py` | ✅ 已改：进程内缓存（Workers 版将改用 KV） |

新增回归测试：`test_content_agents.py`(2)、`test_generate_api.py`(2)。

> 注意：这些修复在**当前 Python 代码**上完成，用于验证逻辑正确性并留作 TS 移植的参考基准。Workers 重写时同样的修复语义会带到 TS 版。

## 3. 目标仓库结构

```
offroad-trip/
├── workers/                    # ★ 新增：CF Workers 后端 (TS)
│   ├── src/
│   │   ├── index.ts            # Hono 路由 (POST /api/generate, GET /api/routes ...)
│   │   ├── workflow.ts         # OffroadTripWorkflow：6 阶段 durable steps
│   │   ├── progress-do.ts      # ProgressCoordinator Durable Object (SSE 推送)
│   │   ├── services/
│   │   │   ├── llm.ts          # 火山方舟 OpenAI 兼容调用 (Secret)
│   │   │   ├── geo.ts          # Nominatim + 坐标表兜底 + KV 缓存
│   │   │   ├── routing.ts      # OSRM + 大圆兜底
│   │   │   ├── weather.ts      # wttr.in
│   │   │   ├── images.ts       # picsum
│   │   │   ├── douyin.ts       # 搜索链接生成
│   │   │   └── cost.ts         # 费用引擎
│   │   ├── prompts/            # planner / scenic / food / history 模板 (直接搬)
│   │   └── db/
│   │       ├── schema.ts       # Drizzle schema (9 表)
│   │       └── queries.ts
│   ├── migrations/0001_init.sql
│   └── wrangler.toml
├── frontend/                   # Vue3：改地图库 + 环境变量
│   └── src/utils/maplibre.js   # ★ 替换 qqmap.js
├── backend/                    # 保留：Python 参考实现 + skill 依赖
├── skill/                      # 保留：可独立运行的 Python 脚本
└── PLAN.md                     # 本文件
```

Python 后端与 skill **保留在仓库**（作为参考实现与独立 CLI），部署上线的是 `workers/` 版本。

## 4. 6 阶段 → Workflow steps 映射

```ts
// workflow.ts (伪代码)
class OffroadTripWorkflow extends WorkflowEntrypoint {
  async run(event, step) {
    const p = new Progress(this.env, event.instanceId) // 写 DO

    const geo = await step.do('geocode', () => geocodeEndpoints(...))      // Nominatim+KV
    await p.emit('geocode', 'done', 10)

    const weather = await step.do('weather', () => fetchWeather(...))       // wttr.in
    await p.emit('weather', 'done', 25)

    const plan = await step.do('planning', () => llmPlan(...))              // LLM(Secret)
    await p.emit('planning', 'done', 50)

    const routed = await step.do('routing', () => osrmRoutes(plan))         // OSRM+POI geocode
    await p.emit('routing', 'done', 70)

    const enriched = await step.do('enrichment', () => enrichAll(routed))   // LLM 并行
    await p.emit('enrichment', 'done', 90)

    const final = await step.do('assembly', () => assemble(enriched))       // picsum+douyin+cost
    await step.do('persist', () => saveToD1(this.env.DB, final))            // D1
    await p.emit('assembly', 'done', 100, final)
  }
}
```

前端交互流程：
1. `POST /api/generate` → Worker 创建 Workflow 实例，返回 `instanceId`
2. `GET /api/stream/:instanceId`（SSE）→ Durable Object 持有连接，Workflow 每步推进度
3. 最终事件带完整路线 + D1 id/share_id；前端跳转 `/route/:id`

> 早期里程碑可先做**内联 SSE Worker**（不拆 Workflow，Worker 内跑完整流水线并流式输出）跑通端到端，再升级为 Workflows+DO 以获得 durability。二选一，Free 计划下 Workflows 版更稳（分步各自独立 CPU 预算）。

## 5. 数据库迁移（SQLAlchemy → D1/Drizzle）

- 9 张表：routes / day_plans / route_segments / pois / meals / hotels / weather_forecasts / story_cards / douyin_links（+ saved_searches）
- 主键沿用 `String(36)` UUID（D1 是 SQLite，天然匹配现有 SQLite 模式）
- `polyline`/`image_urls` 等 JSON 字段 → D1 存 TEXT，读写时 `JSON.stringify/parse`
- 用 Drizzle 定义 schema + 生成 `0001_init.sql` 迁移

## 6. 部署步骤（用你提供的凭据）

```
Account ID : 744c88ae324325511859d8869c5d9e86
Zone ID    : b0dfc31b51bc3b6940d9d8bb659a61a8   → 域名待 API 解析
API Token  : cfat_...（Workers/Pages/D1/Workflows/DO 部署用）
DNS Token  : cfut_...（DNS 记录用）
```

1. `export CLOUDFLARE_API_TOKEN=<API Token>` `export CLOUDFLARE_ACCOUNT_ID=744c88ae...`
2. **D1**：`wrangler d1 create offroadtrip` → 写 database_id 进 wrangler.toml → `wrangler d1 migrations apply offroadtrip --remote`
3. **KV**：`wrangler kv namespace create GEO_CACHE` → 绑定
4. **Secret**：`wrangler secret put SILK_GATEWAY_URL` / `SILK_GATEWAY_KEY`（你的 LLM key）
5. **Worker**：`wrangler deploy`（含 Workflow + DO 绑定）
6. **前端**：`pnpm build` → `wrangler pages deploy frontend/dist --project-name offroadtrip`
7. **域名**：用 DNS Token 配 DNS —— Pages 绑主域，Worker 绑 `api.<域名>`（避免同名路由冲突；CORS 已在代码处理）

## 7. Free 额度可行性

| 产品 | Free 额度 | 本项目用量 | 结论 |
|------|-----------|-----------|------|
| Workers | 100k req/天 | 远低于 | ✅ |
| Workflows | Free 可用 | 每次规划 1 实例 | ✅ |
| Durable Objects | Free(SQLite-backed) | 每任务 1 个 | ✅ |
| D1 | 5GB / 5M 行读/天 | 极低 | ✅ |
| KV | 100k 读/天 | geocode 缓存 | ✅ |
| Pages | 无限请求 / 500 构建/月 | ✅ |

CPU：流水线重 CPU 在解析大 LLM JSON。Workflows 分步 → 每步独立 CPU 预算，Free 计划可行。若追求余量，Workers Paid（$5/月）更稳，但非必需。

## 8. ⚠️ 安全提醒

你在对话中明文粘贴了 API Token / DNS Token。它们已进入本会话记录。**强烈建议部署完成后在 CF 后台 rotate（重置）这两个 token**。后续我们用环境变量引用，不再明文写入任何提交的文件。

## 9. 建议执行顺序

1. ✅【本轮完成】修复 5 个现存 bug + 回归测试（Python 参考实现）
2. 验证 CF 凭据、解析域名、确认 token 权限范围
3. 搭 `workers/` 骨架：Hono + wrangler.toml + D1 schema/migration
4. 移植服务层：先无 key 的 geo/routing/weather/images/douyin/cost，再 LLM
5. 实现 Workflow + Durable Object + SSE
6. 前端换 MapLibre + 改环境变量 + SSE 端点适配
7. 端到端本地 `wrangler dev` 联调
8. 部署 D1/KV/Secret/Worker/Pages + 绑域名
9. 线上冒烟测试一条真实路线
```
```
