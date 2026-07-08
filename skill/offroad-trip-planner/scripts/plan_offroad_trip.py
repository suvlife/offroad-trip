#!/usr/bin/env python3
"""独立越野路线规划脚本 - 可脱离 Web 项目直接运行。

依赖环境变量：
  SILK_GATEWAY_URL  - silk-gateway 地址 (如 https://xxx.workers.dev/v1)
  SILK_GATEWAY_KEY  - silk-gateway API key
  QQ_MAP_KEY        - 腾讯地图 WebService key

用法:
  python plan_offroad_trip.py --from 北京 --to 漠河 --days 7 --vehicle SUV --date 2026-07-08
"""

import argparse
import asyncio
import json
import os
import sys

# Add backend to path so we can reuse the services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))

from app.agents.orchestrator import generate_route_stream


async def main():
    parser = argparse.ArgumentParser(description="越野自驾游路线规划")
    parser.add_argument("--from", dest="departure", required=True, help="出发地")
    parser.add_argument("--to", dest="destination", required=True, help="目的地")
    parser.add_argument("--days", type=int, default=7, help="行程天数")
    parser.add_argument("--vehicle", default="SUV", help="车型 (SUV/越野车/轿车/新能源)")
    parser.add_argument("--date", default="", help="出发日期 (YYYY-MM-DD)")
    parser.add_argument("--budget", type=float, default=10000, help="预算 (元)")
    parser.add_argument("--adults", type=int, default=2, help="成人数")
    parser.add_argument("--children", type=int, default=0, help="儿童数")
    parser.add_argument("--theme", default="回归自然", help="主题")
    parser.add_argument("--output", default="", help="输出文件路径 (默认打印到终端)")
    args = parser.parse_args()

    print(f"🗺️ 正在规划路线: {args.departure} -> {args.destination} ({args.days}天)")
    print(f"🚗 车型: {args.vehicle} | 📅 出发: {args.date} | 💰 预算: {args.budget}元")
    print()

    final_route = None

    async for sse_event in generate_route_stream(
        departure=args.departure,
        destination=args.destination,
        start_date=args.date,
        days=args.days,
        trip_type="越野自驾",
        vehicle_type=args.vehicle,
        adults=args.adults,
        children=args.children,
        budget=args.budget,
        theme=args.theme,
        preferences=["自然风光", "地方美食", "人文历史"],
    ):
        # Parse SSE events
        if not sse_event.startswith("data: "):
            continue

        data_str = sse_event[6:].strip()
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        # Progress events
        if data.get("stage"):
            icon = "✓" if data["status"] == "done" else "⏳"
            print(f"  {icon} [{data['progress']:3d}%] {data['message']}")

        # Final route
        if data.get("route"):
            final_route = data["route"]

    print()

    if not final_route:
        print("❌ 路线生成失败")
        sys.exit(1)

    # Print summary
    print("=" * 60)
    print(f"📍 {final_route.get('title', '路线')}")
    print(f"   {final_route.get('departure')} -> {final_route.get('destination')}")
    print(f"   总里程: {final_route.get('total_distance', 0)}km")
    print(f"   越野难度: {final_route.get('terrain_difficulty', 0)}/5")
    print(f"   自然评分: {final_route.get('nature_score', 0)}/5")
    print()

    if final_route.get("overall_tips"):
        print("💡 整体建议:")
        print(f"   {final_route['overall_tips']}")
        print()

    for day in final_route.get("day_plans", []):
        print(f"─ Day {day['day_number']}: {day.get('theme', '')} ─")
        print(f"  里程: {day.get('day_distance', 0)}km | 风景: {day.get('scenery_description', '')[:50]}")

        for poi in day.get("pois", []):
            print(f"  🎯 {poi.get('name', '')} - {poi.get('feature', '')[:40]}")

        for meal in day.get("meals", []):
            specialty = " [特色]" if meal.get("is_local_specialty") else ""
            print(f"  🍽️ {meal.get('restaurant_name', '')}{specialty} - ¥{meal.get('cost_per_person', 0)}/人")

        print()

    # Save full JSON
    output = json.dumps(final_route, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"📄 完整路线已保存到: {args.output}")
    else:
        print("📄 完整路线 JSON:")
        print(output)


if __name__ == "__main__":
    asyncio.run(main())
