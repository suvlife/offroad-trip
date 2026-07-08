---
name: offroad-trip-planner
description: 越野自驾游路线规划技能。当用户想规划越野自驾路线、自驾游行程、需要沿途景点美食历史推荐时使用。支持自定义出发地、目的地、时间、车型，结合天气给出轻度越野回归自然的路线建议。
triggers:
  - 越野路线规划
  - 自驾游规划
  - offroad trip
  - 越野自驾
  - 规划路线
---

# 越野自驾游路线规划技能

本技能封装了越野智行 (OffroadTrip) 项目的路线规划逻辑，可独立运行或集成到 Web 项目中。

## 能力

根据用户提供的出发地、目的地、时间、车型、偏好，通过 6 阶段智能体流水线生成完整的越野自驾路线：

1. **地理编码** - 腾讯地图 API 将地名转为坐标
2. **天气查询** - 和风天气获取沿途逐日天气预报，影响越野路段决策
3. **路线规划** - LLM (via silk-gateway) 生成路线骨架（车型感知、天气感知）
4. **路线细化** - 腾讯地图驾车路径规划 API 获取实际 polyline/里程/过路费
5. **内容丰富** - 并行 LLM 调用丰富景点特色、美食故事、历史人文
6. **组装** - Unsplash 图片、抖音搜索链接、费用计算、落库

## 使用方式

### 方式一：独立脚本运行

```bash
python skill/offroad-trip-planner/scripts/plan_offroad_trip.py \
  --from 北京 --to 漠河 --days 7 --vehicle SUV --date 2026-07-08
```

需要环境变量：`SILK_GATEWAY_URL`, `SILK_GATEWAY_KEY`, `QQ_MAP_KEY`

### 方式二：调用 Web API

```bash
curl -N -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"departure":"北京","destination":"漠河","start_date":"2026-07-08","days":7,"vehicle_type":"SUV"}'
```

## 输出结构

路线 JSON 包含：
- 路线概览（标题、主题、总里程、越野难度、自然评分、整体建议）
- 逐日行程（主题、里程、沿路风景、路况、天气建议）
- 每日路段（起终点、距离、时间、过路费、polyline 坐标）
- 特色景点（名称、特色说明、趣事典故、历史人物/事件、图片）
- 地方美食（餐厅、菜系、人均、是否特色、背后故事、图片）
- 推荐住宿（名称、地址、价格、评分）
- 历史故事卡片（人物、事件、趣事、完整故事）
- 抖音搜索链接（关键词、跳转 URL）

## 参考文档

- `references/offroad-routes.md` - 越野路线知识库
- `references/prompt-templates.md` - 各 Agent 的 Prompt 模板
- 项目后端代码：`backend/app/agents/` 和 `backend/app/prompts/`
