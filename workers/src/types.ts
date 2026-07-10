/**
 * Shared types + Cloudflare bindings for the OffroadTrip Worker.
 */

export interface Env {
  DB: D1Database;
  GEO_CACHE: KVNamespace;
  TRIP_WORKFLOW: Workflow;
  PROGRESS: DurableObjectNamespace;
  ASSETS: Fetcher;
  AI: Ai;

  // vars
  LLM_MODEL: string;
  SILK_GATEWAY_URL?: string;
  WORKERS_AI_MODEL: string;
  LLM_TIMEOUT_MS: string;
  NOMINATIM_UA: string;

  // secrets (wrangler secret put) — external gateway keys. If unset, Workers AI is used.
  // Two keys supported for failover (e.g. rate limit / quota on the primary).
  SILK_GATEWAY_KEY?: string;
  SILK_GATEWAY_KEY_2?: string;
}

export interface GenerateRequest {
  departure: string;
  destination: string;
  start_date?: string;
  days?: number;
  trip_type?: string;
  vehicle_type?: string;
  adults?: number;
  children?: number;
  budget?: number;
  theme?: string;
  preferences?: string[];
  session_id?: string;
}

export interface GeoPoint {
  lat: number;
  lng: number;
  city?: string;
  province?: string;
}

export interface Segment {
  from_name: string;
  to_name: string;
  sort_order: number;
  distance?: number;
  duration?: number;
  toll_cost?: number;
  fuel_cost?: number;
  polyline?: [number, number][];
}

export interface Poi {
  id?: string;
  type?: string;
  category?: string;
  name: string;
  lat?: number;
  lng?: number;
  description?: string;
  feature?: string;
  anecdote?: string;
  historical_figure?: string;
  historical_event?: string;
  duration_minutes?: number;
  sort_order?: number;
  image_url?: string;
}

export interface Meal {
  type?: string;
  restaurant_name: string;
  cuisine_type?: string;
  cost_per_person?: number;
  is_local_specialty?: boolean;
  recommendation?: string;
  story?: string;
  image_url?: string;
}

export interface Hotel {
  name: string;
  address?: string;
  price_per_night?: number;
  rating?: number;
  lat?: number;
  lng?: number;
}

export interface DayPlan {
  day_number: number;
  date?: string;
  theme?: string;
  day_distance?: number;
  day_duration?: number;
  scenery_description?: string;
  terrain_note?: string;
  weather_advisory?: string;
  segments: Segment[];
  pois: Poi[];
  meals: Meal[];
  hotels: Hotel[];
}

export interface StoryCard {
  related_city?: string;
  day_number?: number;
  figure?: string;
  event?: string;
  anecdote?: string;
  story_text?: string;
}

export interface DouyinLink {
  keyword: string;
  search_url: string;
  qr_code_data: string;
  label: string;
  related_type: string;
  related_id: string;
}

export interface RouteData {
  id?: string;
  share_id?: string;
  title: string;
  theme?: string;
  departure: string;
  destination: string;
  vehicle_type?: string;
  trip_type?: string;
  adults?: number;
  children?: number;
  budget?: number;
  status?: string;
  terrain_difficulty?: number;
  nature_score?: number;
  overall_tips?: string;
  total_distance?: number;
  total_duration?: number;
  day_plans: DayPlan[];
  story_cards?: StoryCard[];
  douyin_links?: DouyinLink[];
  cost_breakdown?: CostBreakdown;
  _weather_map?: Record<string, WeatherForecast[]>;
}

export interface CostBreakdown {
  fuel: number;
  toll: number;
  hotel: number;
  meal: number;
  ticket: number;
  total: number;
  breakdown: Record<string, string>;
}

export interface WeatherForecast {
  date: string;
  temperature_high: number;
  temperature_low: number;
  weather_condition: string;
  icon: string;
  humidity: number;
  wind_speed: number;
  precipitation: number;
}

export interface WeatherData {
  city: string;
  forecasts: WeatherForecast[];
  error?: string;
}

export interface ProgressEvent {
  stage: string;
  status: "running" | "done" | "error";
  message: string;
  progress: number;
  route?: RouteData | null;
  error?: string;
}
