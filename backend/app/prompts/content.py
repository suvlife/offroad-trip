"""Prompt templates for content enrichment agents (Stage 5).

Scenic, food, and history agents enrich the route skeleton with detailed content.
"""

# ─── Scenic Agent ───────────────────────────────────────────────────────────

SCENIC_SYSTEM = """你是一位资深旅游攻略作家，擅长发掘景点的独特魅力。
你不仅介绍景点，更注重讲述"为什么值得去"——它的特色、故事、最佳体验方式。
返回严格JSON格式。"""

SCENIC_USER_TEMPLATE = """为以下城市的景点补充详细信息：

城市：{city}
景点列表：{scenic_list}

请为每个景点返回JSON：
```json
{{
  "pois": [
    {{
      "name": "景点名称",
      "feature": "这个景点的核心特色，为什么值得专门去，50字以内",
      "anecdote": "关于这个景点的趣事或典故，80字以内",
      "historical_figure": "相关历史人物（没有则空）",
      "historical_event": "相关历史事件（没有则空）",
      "description": "更详细的介绍，100字以内",
      "duration_minutes": 建议游玩分钟数
    }}
  ]
}}
```
只返回JSON。"""


# ─── Food Agent ─────────────────────────────────────────────────────────────

FOOD_SYSTEM = """你是一位美食文化研究者，深谙中国各地饮食文化。
你不仅推荐美食，更讲述每道菜背后的故事、历史、文化内涵。
返回严格JSON格式。"""

FOOD_USER_TEMPLATE = """为以下城市的美食补充详细信息：

城市：{city}
美食列表：{food_list}

请为每道美食/餐厅返回JSON：
```json
{{
  "meals": [
    {{
      "restaurant_name": "餐厅或菜品名",
      "cuisine_type": "菜系",
      "is_local_specialty": true/false,
      "story": "这道美食背后的故事、起源、文化内涵，100字以内",
      "recommendation": "推荐理由和品尝建议",
      "cost_per_person": 人均消费
    }}
  ]
}}
```
只返回JSON。"""


# ─── History Agent ──────────────────────────────────────────────────────────

HISTORY_SYSTEM = """你是一位历史人文专家，擅长挖掘旅途中的历史故事。
你能把枯燥的历史变成生动有趣的故事，让旅行更有深度和文化底蕴。
返回严格JSON格式。"""

HISTORY_USER_TEMPLATE = """为以下城市的旅途挖掘历史人文故事：

城市：{city}
途经景点：{scenic_names}

请挖掘这座城市和景点的历史故事，返回1-3个故事卡片：
```json
{{
  "stories": [
    {{
      "figure": "相关历史人物（没有则空）",
      "event": "相关历史事件（没有则空）",
      "anecdote": "趣事标题，10字以内",
      "story_text": "完整故事，生动有趣，200字以内",
      "related_city": "{city}"
    }}
  ]
}}
```
要求：
- 故事要生动有趣，像朋友讲故事一样
- 可以是历史人物轶事、重大事件、民间传说
- 与这座城市或途经景点相关
只返回JSON。"""


# ─── Weather Advisory Agent (uses weather data for route decisions) ──────────

WEATHER_DECISION_SYSTEM = """你是一位越野驾驶安全顾问，根据天气情况给出出行建议。
你了解雨雪雾天对越野路段的影响，能给出务实的调整建议。"""


WEATHER_DECISION_TEMPLATE = """根据以下天气信息，给出越野自驾出行建议：

路线：{departure} -> {destination}
日期：{start_date}，共{days}天
车型：{vehicle_type}

沿途天气：
{weather_details}

请给出：
1. 是否适合越野路段
2. 需要注意的天气风险
3. 路线调整建议（如需）
简短回复，200字以内。"""


def build_scenic_prompt(city: str, scenic_list: str) -> tuple:
    return SCENIC_SYSTEM, SCENIC_USER_TEMPLATE.format(city=city, scenic_list=scenic_list)


def build_food_prompt(city: str, food_list: str) -> tuple:
    return FOOD_SYSTEM, FOOD_USER_TEMPLATE.format(city=city, food_list=food_list)


def build_history_prompt(city: str, scenic_names: str) -> tuple:
    return HISTORY_SYSTEM, HISTORY_USER_TEMPLATE.format(city=city, scenic_names=scenic_names)


def build_weather_decision_prompt(
    departure: str, destination: str, start_date: str, days: int,
    vehicle_type: str, weather_details: str,
) -> tuple:
    return WEATHER_DECISION_SYSTEM, WEATHER_DECISION_TEMPLATE.format(
        departure=departure, destination=destination, start_date=start_date,
        days=days, vehicle_type=vehicle_type, weather_details=weather_details,
    )
