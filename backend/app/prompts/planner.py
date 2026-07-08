"""Prompt templates for the route planning agent (Stage 3: route skeleton).

The planner agent creates the route skeleton: city sequence, daily segments,
off-road difficulty ratings, and natural scenery descriptions.
It is vehicle-aware (SUV can do unpaved, sedan stays paved).
"""

PLANNER_SYSTEM = """你是越野自驾游路线规划专家。直接输出路线JSON，不要冗长推理。

规划原则：
1. 回归自然：优先山林、草原、河谷等自然风光
2. 轻度越野：SUV可走非铺装路，轿车只走铺装路
3. 合理节奏：每天200-400km
4. 天气优先：雨天降级越野路段

直接返回JSON，不要额外说明。"""

PLANNER_USER_TEMPLATE = """请为以下越野自驾游需求设计一条路线方案：

出发地：{departure}
目的地：{destination}
出发日期：{start_date}
行程天数：{days}天
旅行类型：{trip_type}
车型：{vehicle_type}
成人：{adults}人，儿童：{children}人
预算：{budget}元
主题偏好：{theme}
特别偏好：{preferences}

天气情况：
{weather_info}

地理信息：
{geo_info}

请返回JSON，格式如下：
```json
{{
  "title": "路线名称（要生动有吸引力）",
  "theme": "路线主题",
  "total_distance": 总里程数字(公里),
  "total_duration": 总驾驶时长数字(小时),
  "terrain_difficulty": 地形难度1-5(1=全铺装, 3=部分非铺装轻度越野, 5=硬核越野),
  "nature_score": 自然风光评分1-5,
  "overall_tips": "整体游玩建议，200字以内，包括最佳季节、越野注意、装备、预算分配等",
  "day_plans": [
    {{
      "day_number": 1,
      "date": "第1天或具体日期",
      "theme": "当天主题，如'京承高速秋色之旅'",
      "day_distance": 当天里程(公里),
      "day_duration": 当天驾驶时长(小时),
      "scenery_description": "沿路风景描述，生动描绘途中可见的自然风光，100字以内",
      "terrain_note": "路况说明：铺装/非铺装/越野路段比例，注意事项",
      "segments": [
        {{
          "from_name": "起点名称",
          "to_name": "终点名称",
          "sort_order": 0
        }}
      ],
      "pois": [
        {{
          "type": "scenic",
          "category": "scenic/nature/history/viewpoint",
          "name": "景点名称",
          "description": "简短介绍",
          "feature": "这个景点的特色，为什么值得专门去",
          "duration_minutes": 建议游玩分钟数,
          "sort_order": 0
        }}
      ],
      "meals": [
        {{
          "type": "breakfast/lunch/dinner",
          "restaurant_name": "餐厅或菜品名",
          "cuisine_type": "菜系",
          "cost_per_person": 人均消费,
          "is_local_specialty": true/false,
          "recommendation": "推荐理由",
          "story": "这道美食背后的故事或典故"
        }}
      ],
      "hotels": [
        {{
          "name": "酒店名称",
          "address": "大致地址",
          "price_per_night": 每晚价格,
          "rating": 评分
        }}
      ]
    }}
  ]
}}
```

设计要求：
- 共{days}天的完整行程
- 每天包含2-4个景点、3餐推荐、1-2家酒店
- 景点的feature字段务必说明"为什么值得去"
- 美食的story字段讲讲这道菜背后的故事
- 越野路段在terrain_note中说明
- 确保路线整体连贯合理，每天的segments首尾相接

只返回JSON，不要其他文字。"""


def build_planner_prompt(
    departure: str,
    destination: str,
    start_date: str,
    days: int,
    trip_type: str,
    vehicle_type: str,
    adults: int,
    children: int,
    budget: float,
    theme: str,
    preferences: list,
    weather_info: str,
    geo_info: str,
) -> str:
    """Build the user prompt for the route planner agent."""
    prefs_str = "、".join(preferences) if preferences else "无特殊偏好"
    return PLANNER_USER_TEMPLATE.format(
        departure=departure,
        destination=destination,
        start_date=start_date,
        days=days,
        trip_type=trip_type,
        vehicle_type=vehicle_type,
        adults=adults,
        children=children,
        budget=budget,
        theme=theme,
        preferences=prefs_str,
        weather_info=weather_info,
        geo_info=geo_info,
    )
