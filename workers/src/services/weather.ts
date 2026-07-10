/**
 * Weather service — free / no-key via wttr.in.
 * Ported from backend/app/services/weather_service.py (wttr.in path) +
 * weather_agent.py advisory logic (per-city, for per-day assignment).
 */

import type { WeatherData, WeatherForecast } from "../types";

export async function getWeather(city: string, days = 7): Promise<WeatherData> {
  try {
    const resp = await fetch(`https://wttr.in/${encodeURIComponent(city)}?format=j1`);
    if (resp.ok) {
      const data = (await resp.json()) as any;
      const forecasts: WeatherForecast[] = (data.weather ?? []).slice(0, days).map((day: any) => {
        const hourly = day.hourly?.[0] ?? {};
        return {
          date: day.date ?? "",
          temperature_high: parseFloat(day.maxtempC ?? "0"),
          temperature_low: parseFloat(day.mintempC ?? "0"),
          weather_condition: hourly.weatherDesc?.[0]?.value ?? "",
          icon: hourly.weatherCode ?? "",
          humidity: parseFloat(hourly.humidity ?? "0"),
          wind_speed: parseFloat(hourly.windspeedKmph ?? "0"),
          precipitation: parseFloat(hourly.precipMM ?? "0"),
        };
      });
      return { city, forecasts };
    }
  } catch (e) {
    console.error(`wttr.in error for ${city}: ${e}`);
  }
  return { city, forecasts: [], error: "Weather data unavailable" };
}

export async function fetchWeatherForCities(cities: string[], days: number): Promise<Record<string, WeatherData>> {
  const results = await Promise.allSettled(cities.map((c) => getWeather(c, days)));
  const map: Record<string, WeatherData> = {};
  cities.forEach((city, i) => {
    const r = results[i];
    map[city] = r.status === "fulfilled" ? r.value : { city, forecasts: [], error: String(r.reason) };
  });
  return map;
}

/** Rule-based off-road advisory for a single city's forecast. */
export function getWeatherAdvisory(data: WeatherData | undefined): string {
  if (!data || !data.forecasts?.length) {
    return "天气数据暂不可用，建议出发前查看实时天气。";
  }
  const advisories: string[] = [];
  for (const day of data.forecasts) {
    const cond = day.weather_condition || "";
    const precip = day.precipitation || 0;
    const tempLow = day.temperature_low || 0;
    const notes: string[] = [];

    if (/大雨|暴雨|大暴雨|Heavy rain|Torrential/i.test(cond)) {
      notes.push("大雨天气，非铺装路面易泥泞打滑，建议避开越野路段，走铺装公路");
    } else if (/中雨|阵雨|rain|shower/i.test(cond)) {
      notes.push("有降雨，轻度越野路段需谨慎驾驶，注意防滑");
    } else if (/雪|暴雪|snow/i.test(cond)) {
      notes.push(`降雪天气（最低${tempLow}°C），需雪地胎/防滑链，越野路段建议绕行`);
    } else if (/雾|霾|fog|mist/i.test(cond)) {
      notes.push("能见度低，山路弯道需减速慢行，开启雾灯");
    } else if (precip > 10) {
      notes.push(`降水量较大（${precip}mm），注意路面积水`);
    } else {
      notes.push("天气良好，适合越野及户外活动");
    }
    if (tempLow < 0) notes.push(`气温较低（${tempLow}°C），注意防寒保暖，检查防冻液`);

    advisories.push(`${day.date}: ${notes.join("；")}`);
  }
  return advisories.join("；\n");
}

/** Advisory for a specific city (partial-match fallback), for per-day assignment. */
export function advisoryForCity(weatherMap: Record<string, WeatherData>, city: string): string {
  let data = weatherMap[city];
  if (!data && city) {
    for (const [name, d] of Object.entries(weatherMap)) {
      if (name && (name.includes(city) || city.includes(name))) {
        data = d;
        break;
      }
    }
  }
  return getWeatherAdvisory(data);
}

/** Concise weather block for the planner prompt. */
export function formatWeatherForPlanner(weatherMap: Record<string, WeatherData>): string {
  const lines: string[] = [];
  for (const [city, data] of Object.entries(weatherMap)) {
    if (!data.forecasts?.length) {
      lines.push(`${city}: 天气数据暂不可用`);
      continue;
    }
    const wl = data.forecasts.slice(0, 5).map(
      (f) => `  ${f.date}: ${f.weather_condition}, ${f.temperature_low}~${f.temperature_high}°C, 降水${f.precipitation}mm`
    );
    lines.push(`${city}:\n${wl.join("\n")}`);
  }
  return lines.length ? lines.join("\n") : "天气数据暂不可用";
}
