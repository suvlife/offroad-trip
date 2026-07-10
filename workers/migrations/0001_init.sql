-- OffroadTrip D1 schema (migrated from SQLAlchemy models/route.py).
-- SQLite / D1. UUID text PKs. JSON columns stored as TEXT.

CREATE TABLE IF NOT EXISTS routes (
  id TEXT PRIMARY KEY,
  share_id TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  departure TEXT NOT NULL,
  destination TEXT NOT NULL,
  total_distance REAL DEFAULT 0,
  total_duration REAL DEFAULT 0,
  trip_type TEXT DEFAULT '越野自驾',
  theme TEXT DEFAULT '回归自然',
  vehicle_type TEXT DEFAULT 'SUV',
  terrain_difficulty INTEGER DEFAULT 2,
  nature_score INTEGER DEFAULT 4,
  adults INTEGER DEFAULT 2,
  children INTEGER DEFAULT 0,
  budget REAL DEFAULT 0,
  status TEXT DEFAULT 'draft',
  overall_tips TEXT DEFAULT '',
  cost_breakdown TEXT DEFAULT '',          -- JSON
  created_at TEXT DEFAULT (datetime('now')),
  view_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_routes_share ON routes(share_id);
CREATE INDEX IF NOT EXISTS idx_routes_created ON routes(created_at DESC);

CREATE TABLE IF NOT EXISTS day_plans (
  id TEXT PRIMARY KEY,
  route_id TEXT NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
  day_number INTEGER NOT NULL,
  date TEXT DEFAULT '',
  theme TEXT DEFAULT '',
  day_distance REAL DEFAULT 0,
  day_duration REAL DEFAULT 0,
  day_cost REAL DEFAULT 0,
  weather_advisory TEXT DEFAULT '',
  scenery_description TEXT DEFAULT '',
  terrain_note TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_dayplans_route ON day_plans(route_id);

CREATE TABLE IF NOT EXISTS route_segments (
  id TEXT PRIMARY KEY,
  day_plan_id TEXT NOT NULL REFERENCES day_plans(id) ON DELETE CASCADE,
  from_name TEXT NOT NULL,
  to_name TEXT NOT NULL,
  distance REAL DEFAULT 0,
  duration REAL DEFAULT 0,
  toll_cost REAL DEFAULT 0,
  fuel_cost REAL DEFAULT 0,
  polyline TEXT DEFAULT '[]',              -- JSON [[lat,lng],...]
  sort_order INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_segments_day ON route_segments(day_plan_id);

CREATE TABLE IF NOT EXISTS pois (
  id TEXT PRIMARY KEY,
  day_plan_id TEXT NOT NULL REFERENCES day_plans(id) ON DELETE CASCADE,
  segment_id TEXT REFERENCES route_segments(id) ON DELETE SET NULL,
  type TEXT NOT NULL DEFAULT 'scenic',
  category TEXT DEFAULT 'scenic',
  name TEXT NOT NULL,
  lat REAL DEFAULT 0,
  lng REAL DEFAULT 0,
  rating REAL DEFAULT 0,
  price_level TEXT DEFAULT '',
  image_url TEXT DEFAULT '',
  description TEXT DEFAULT '',
  source_url TEXT DEFAULT '',
  booking_url TEXT DEFAULT '',
  duration_minutes INTEGER DEFAULT 0,
  sort_order INTEGER DEFAULT 0,
  feature TEXT DEFAULT '',
  anecdote TEXT DEFAULT '',
  historical_figure TEXT DEFAULT '',
  historical_event TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_pois_day ON pois(day_plan_id);

CREATE TABLE IF NOT EXISTS meals (
  id TEXT PRIMARY KEY,
  day_plan_id TEXT NOT NULL REFERENCES day_plans(id) ON DELETE CASCADE,
  type TEXT NOT NULL DEFAULT 'lunch',
  restaurant_name TEXT NOT NULL,
  cuisine_type TEXT DEFAULT '',
  cost_per_person REAL DEFAULT 0,
  image_url TEXT DEFAULT '',
  rating REAL DEFAULT 0,
  recommendation TEXT DEFAULT '',
  is_local_specialty INTEGER DEFAULT 0,
  story TEXT DEFAULT '',
  image_urls TEXT DEFAULT '[]'             -- JSON
);
CREATE INDEX IF NOT EXISTS idx_meals_day ON meals(day_plan_id);

CREATE TABLE IF NOT EXISTS hotels (
  id TEXT PRIMARY KEY,
  day_plan_id TEXT NOT NULL REFERENCES day_plans(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  lat REAL DEFAULT 0,
  lng REAL DEFAULT 0,
  price_per_night REAL DEFAULT 0,
  rating REAL DEFAULT 0,
  image_url TEXT DEFAULT '',
  booking_url TEXT DEFAULT '',
  address TEXT DEFAULT '',
  phone TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_hotels_day ON hotels(day_plan_id);

CREATE TABLE IF NOT EXISTS weather_forecasts (
  id TEXT PRIMARY KEY,
  route_id TEXT NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
  city_name TEXT NOT NULL,
  date TEXT NOT NULL,
  temperature_high REAL DEFAULT 0,
  temperature_low REAL DEFAULT 0,
  weather_condition TEXT DEFAULT '',
  icon TEXT DEFAULT '',
  humidity REAL DEFAULT 0,
  wind_speed REAL DEFAULT 0,
  precipitation REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_weather_route ON weather_forecasts(route_id);

CREATE TABLE IF NOT EXISTS story_cards (
  id TEXT PRIMARY KEY,
  route_id TEXT NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
  related_city TEXT DEFAULT '',
  day_number INTEGER DEFAULT 0,
  figure TEXT DEFAULT '',
  event TEXT DEFAULT '',
  anecdote TEXT DEFAULT '',
  story_text TEXT DEFAULT '',
  image_url TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_stories_route ON story_cards(route_id);

CREATE TABLE IF NOT EXISTS douyin_links (
  id TEXT PRIMARY KEY,
  route_id TEXT NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
  related_type TEXT NOT NULL DEFAULT 'poi',
  related_id TEXT DEFAULT '',
  keyword TEXT NOT NULL,
  search_url TEXT DEFAULT '',
  qr_code_data TEXT DEFAULT '',
  label TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_douyin_route ON douyin_links(route_id);

CREATE TABLE IF NOT EXISTS saved_searches (
  id TEXT PRIMARY KEY,
  session_id TEXT DEFAULT '',
  departure_city TEXT NOT NULL,
  destination_city TEXT NOT NULL,
  start_date TEXT DEFAULT '',
  days INTEGER DEFAULT 3,
  trip_type TEXT DEFAULT '越野自驾',
  adults INTEGER DEFAULT 2,
  children INTEGER DEFAULT 0,
  vehicle_type TEXT DEFAULT 'SUV',
  budget REAL DEFAULT 0,
  theme TEXT DEFAULT '',
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_search_session ON saved_searches(session_id);
