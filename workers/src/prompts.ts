/**
 * Prompt templates — ported verbatim from backend/app/prompts/{planner,content}.py.
 */

import type { GenerateRequest } from "./types";

export const PLANNER_SYSTEM = `你是越野自驾游路线规划专家。直接输出路线JSON，不要冗长推理。

规划原则：
1. 回归自然：优先山林、草原、河谷等自然风光
2. 轻度越野：SUV可走非铺装路，轿车只走铺装路
3. 合理节奏：每天200-400km
4. 天气优先：雨天降级越野路段

直接返回JSON，不要额外说明。`;

export function buildPlannerPrompt(req: Required<Pick<GenerateRequest,
  "departure" | "destination" | "days" | "trip_type" | "vehicle_type" | "adults" | "children" | "budget" | "theme">> & {
  start_date: string;
  preferences: string[];
  weather_info: string;
  geo_info: string;
}): string {
  const prefs = req.preferences.length ? req.preferences.join("、") : "无特殊偏好";
  return `请为以下越野自驾游需求设计一条路线方案：

出发地：${req.departure}
目的地：${req.destination}
出发日期：${req.start_date}
行程天数：${req.days}天
旅行类型：${req.trip_type}
车型：${req.vehicle_type}
成人：${req.adults}人，儿童：${req.children}人
预算：${req.budget}元
主题偏好：${req.theme}
特别偏好：${prefs}

天气情况：
${req.weather_info}

地理信息：
${req.geo_info}

请返回JSON，格式如下：
\`\`\`json
{
  "title": "路线名称（要生动有吸引力）",
  "theme": "路线主题",
  "total_distance": 总里程数字(公里),
  "total_duration": 总驾驶时长数字(小时),
  "terrain_difficulty": 地形难度1-5(1=全铺装, 3=部分非铺装轻度越野, 5=硬核越野),
  "nature_score": 自然风光评分1-5,
  "overall_tips": "整体游玩建议，200字以内，包括最佳季节、越野注意、装备、预算分配等",
  "day_plans": [
    {
      "day_number": 1,
      "date": "第1天或具体日期",
      "theme": "当天主题，如'京承高速秋色之旅'",
      "day_distance": 当天里程(公里),
      "day_duration": 当天驾驶时长(小时),
      "scenery_description": "沿路风景描述，生动描绘途中可见的自然风光，100字以内",
      "terrain_note": "路况说明：铺装/非铺装/越野路段比例，注意事项",
      "segments": [
        { "from_name": "起点名称", "to_name": "终点名称", "sort_order": 0 }
      ],
      "pois": [
        {
          "type": "scenic",
          "category": "scenic/nature/history/viewpoint",
          "name": "景点名称",
          "description": "简短介绍",
          "feature": "这个景点的特色，为什么值得专门去",
          "duration_minutes": 建议游玩分钟数,
          "sort_order": 0
        }
      ],
      "meals": [
        {
          "type": "breakfast/lunch/dinner",
          "restaurant_name": "餐厅或菜品名",
          "cuisine_type": "菜系",
          "cost_per_person": 人均消费,
          "is_local_specialty": true,
          "recommendation": "推荐理由",
          "story": "这道美食背后的故事或典故"
        }
      ],
      "hotels": [
        { "name": "酒店名称", "address": "大致地址", "price_per_night": 每晚价格, "rating": 评分 }
      ]
    }
  ]
}
\`\`\`

设计要求：
- 共${req.days}天的完整行程
- 每天包含2-4个景点、3餐推荐、1-2家酒店
- 景点的feature字段务必说明"为什么值得去"
- 美食的story字段讲讲这道菜背后的故事
- 越野路段在terrain_note中说明
- 确保路线整体连贯合理，每天的segments首尾相接

只返回JSON，不要其他文字。`;
}

export const SCENIC_SYSTEM = `你是一位资深旅游攻略作家，擅长发掘景点的独特魅力。
你不仅介绍景点，更注重讲述"为什么值得去"——它的特色、故事、最佳体验方式。
返回严格JSON格式。`;

export function buildScenicPrompt(city: string, scenicList: string): string {
  return `为以下城市的景点补充详细信息：

城市：${city}
景点列表：${scenicList}

请为每个景点返回JSON：
\`\`\`json
{
  "pois": [
    {
      "name": "景点名称",
      "feature": "这个景点的核心特色，为什么值得专门去，50字以内",
      "anecdote": "关于这个景点的趣事或典故，80字以内",
      "historical_figure": "相关历史人物（没有则空）",
      "historical_event": "相关历史事件（没有则空）",
      "description": "更详细的介绍，100字以内",
      "duration_minutes": 建议游玩分钟数
    }
  ]
}
\`\`\`
只返回JSON。`;
}

export const FOOD_SYSTEM = `你是一位美食文化研究者，深谙中国各地饮食文化。
你不仅推荐美食，更讲述每道菜背后的故事、历史、文化内涵。
返回严格JSON格式。`;

export function buildFoodPrompt(city: string, foodList: string): string {
  return `为以下城市的美食补充详细信息：

城市：${city}
美食列表：${foodList}

请为每道美食/餐厅返回JSON：
\`\`\`json
{
  "meals": [
    {
      "restaurant_name": "餐厅或菜品名",
      "cuisine_type": "菜系",
      "is_local_specialty": true,
      "story": "这道美食背后的故事、起源、文化内涵，100字以内",
      "recommendation": "推荐理由和品尝建议",
      "cost_per_person": 人均消费
    }
  ]
}
\`\`\`
只返回JSON。`;
}

export const HISTORY_SYSTEM = `你是一位历史人文专家，擅长挖掘旅途中的历史故事。
你能把枯燥的历史变成生动有趣的故事，让旅行更有深度和文化底蕴。
返回严格JSON格式。`;

export function buildHistoryPrompt(city: string, scenicNames: string): string {
  return `为以下城市的旅途挖掘历史人文故事：

城市：${city}
途经景点：${scenicNames}

请挖掘这座城市和景点的历史故事，返回1-3个故事卡片：
\`\`\`json
{
  "stories": [
    {
      "figure": "相关历史人物（没有则空）",
      "event": "相关历史事件（没有则空）",
      "anecdote": "趣事标题，10字以内",
      "story_text": "完整故事，生动有趣，200字以内",
      "related_city": "${city}"
    }
  ]
}
\`\`\`
要求：
- 故事要生动有趣，像朋友讲故事一样
- 可以是历史人物轶事、重大事件、民间传说
- 与这座城市或途经景点相关
只返回JSON。`;
}
