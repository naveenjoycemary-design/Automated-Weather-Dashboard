import os
import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh

# =============================================================
# CONFIG
# =============================================================

API_KEY = "efd6b4dcc0f1b762d34a167b399098a5"
DB_URL  = "mysql+pymysql://root:IGhIAxQDDVFToxfYQachvKAFVphAiAkr@maglev.proxy.rlwy.net:50970/railway"

engine = create_engine(DB_URL, pool_pre_ping=True)
IST    = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(IST).replace(tzinfo=None)

# =============================================================
# COUNTRY / CITY MAP  (min 10 cities each)
# =============================================================

COUNTRY_CITY = {
    "India": {
        "code": "IN",
        "cities": ["Bangalore","Delhi","Mumbai","Chennai","Hyderabad",
                   "Kolkata","Pune","Ahmedabad","Jaipur","Trichy",
                   "Surat","Lucknow","Bhopal","Patna","Nagpur"]
    },
    "USA": {
        "code": "US",
        "cities": ["New York","Los Angeles","Chicago","Houston","Phoenix",
                   "San Francisco","San Diego","Dallas","Seattle","Boston",
                   "Miami","Atlanta","Denver","Portland","Las Vegas"]
    },
    "UK": {
        "code": "GB",
        "cities": ["London","Manchester","Birmingham","Liverpool",
                   "Leeds","Bristol","Nottingham","Sheffield",
                   "Edinburgh","Glasgow","Cardiff","Oxford"]
    },
    "Japan": {
        "code": "JP",
        "cities": ["Tokyo","Osaka","Kyoto","Yokohama","Sapporo",
                   "Nagoya","Kobe","Fukuoka","Sendai","Hiroshima",
                   "Nara","Kawasaki"]
    },
    "Australia": {
        "code": "AU",
        "cities": ["Sydney","Melbourne","Brisbane","Perth","Adelaide",
                   "Canberra","Gold Coast","Newcastle","Hobart","Darwin",
                   "Wollongong","Geelong"]
    }
}

# =============================================================
# PAGE CONFIG
# =============================================================

st.set_page_config(page_title="Weather Analytics Pro", page_icon="🌦️", layout="wide")

# =============================================================
# GLOBAL CSS
# =============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0a1a 0%, #0d1b2a 50%, #0a1628 100%) !important;
    border-right: 1px solid rgba(99,179,237,0.15) !important;
}
section[data-testid="stSidebar"] * { color: white !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label { color: rgba(255,255,255,0.7) !important; font-size:13px; }

[data-testid="metric-container"] {
    background: linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid rgba(99,179,237,0.2);
    border-radius: 20px;
    padding: 20px 22px !important;
    backdrop-filter: blur(12px);
    transition: transform 0.2s, border-color 0.2s;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    border-color: rgba(99,179,237,0.45);
}
[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 700 !important; font-family: 'Outfit', sans-serif !important; }
[data-testid="stMetricLabel"] { font-size: 0.8rem !important; opacity: 0.75; }

.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: rgba(255,255,255,0.04);
    border-radius: 14px;
    padding: 6px;
    border: 1px solid rgba(255,255,255,0.08);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 9px 24px;
    font-weight: 600;
    font-size: 14px;
    color: rgba(255,255,255,0.6) !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1a56db, #0ea5e9) !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(14,165,233,0.35);
}

.stDataFrame { border-radius: 14px; overflow: hidden; }
hr { border-color: rgba(255,255,255,0.08) !important; }

.badge {
    display: inline-block;
    padding: 5px 16px;
    border-radius: 30px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.wcard {
    background: linear-gradient(160deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 20px 14px;
    text-align: center;
    color: white;
    transition: transform 0.25s, box-shadow 0.25s;
    box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    backdrop-filter: blur(10px);
}
.wcard:hover { transform: translateY(-4px); box-shadow: 0 8px 32px rgba(14,165,233,0.2); }
.wcard .label { font-size: 12px; opacity: 0.65; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.06em; }
.wcard .icon  { font-size: 34px; margin: 8px 0; }
.wcard .temp  { font-size: 24px; font-weight: 800; }
.wcard .sub   { font-size: 12px; opacity: 0.6; margin-top: 5px; }

.graph-label {
    background: linear-gradient(90deg, rgba(14,165,233,0.12), rgba(14,165,233,0.02));
    border-left: 3px solid #0ea5e9;
    border-radius: 10px;
    padding: 10px 18px;
    margin-bottom: 12px;
    color: white;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.02em;
}

/* Walkthrough cards */
.tour-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 20px;
    padding: 26px 22px;
    color: white;
    margin-bottom: 16px;
    transition: border-color 0.2s;
}
.tour-card:hover { border-color: rgba(14,165,233,0.4); }
.tour-step { font-size: 11px; font-weight: 700; color: #0ea5e9; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; }
.tour-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
.tour-desc  { font-size: 14px; opacity: 0.75; line-height: 1.6; }

.alert-box {
    padding: 14px 20px;
    border-radius: 14px;
    margin: 8px 0;
    font-size: 14px;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# =============================================================
# CHART THEME  (inspired by the ECharts / appealing-charts style)
# =============================================================

DARK_BG   = "#0d1117"
CARD_BG   = "#111827"
CARD_BG2  = "#1a2235"
GRID_COL  = "#1e2d3d"
TEXT_COL  = "#e2e8f0"
MUTED     = "#64748b"
ACCENT1   = "#38bdf8"   # sky blue
ACCENT2   = "#f97316"   # orange
ACCENT3   = "#22d3ee"   # cyan
ACCENT4   = "#a78bfa"   # violet
ACCENT5   = "#4ade80"   # green
ACCENT6   = "#fb7185"   # rose

PALETTE = [ACCENT1, ACCENT5, ACCENT2, ACCENT4, ACCENT3, ACCENT6]

def style_ax(ax, fig, title="", subtitle=""):
    ax.set_facecolor(CARD_BG2)
    fig.patch.set_facecolor(DARK_BG)
    ax.tick_params(colors=TEXT_COL, labelsize=9, length=3)
    ax.xaxis.label.set_color(TEXT_COL)
    ax.yaxis.label.set_color(TEXT_COL)
    if title:
        ax.set_title(title, color=TEXT_COL, fontweight="bold", fontsize=13,
                     pad=14, loc="left", fontfamily="DejaVu Sans")
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)
        spine.set_linewidth(0.8)
    ax.grid(True, linestyle="--", alpha=0.25, color=GRID_COL, linewidth=0.8)
    ax.set_axisbelow(True)

def rounded_bar(ax, x, height, width, color, alpha=1.0, radius=0.05):
    """Draw bars with a slightly rounded look using fancybbox patches."""
    for xi, hi in zip(x, height):
        ax.bar(xi, hi, width=width, color=color, alpha=alpha,
               linewidth=0, zorder=3)

# =============================================================
# DYNAMIC BACKGROUND  (weather-condition aware)
# =============================================================

BG_IMAGES = {
    "thunderstorm": "https://images.pexels.com/photos/1162251/pexels-photo-1162251.jpeg",
    "rain_night":   "https://images.pexels.com/photos/110874/pexels-photo-110874.jpeg",
    "rain_day":     "https://images.pexels.com/photos/2448749/pexels-photo-2448749.jpeg",
    "drizzle":      "https://images.pexels.com/photos/빗/1463530/pexels-photo-1463530.jpeg",
    "snow":         "https://images.pexels.com/photos/209831/pexels-photo-209831.jpeg",
    "mist":         "https://images.pexels.com/photos/靄/167699/pexels-photo-167699.jpeg",
    "fog":          "https://images.pexels.com/photos/靄/167699/pexels-photo-167699.jpeg",
    "haze":         "https://images.pexels.com/photos/167699/pexels-photo-167699.jpeg",
    "smoke":        "https://images.pexels.com/photos/167699/pexels-photo-167699.jpeg",
    "dust":         "https://images.pexels.com/photos/1643409/pexels-photo-1643409.jpeg",
    "sand":         "https://images.pexels.com/photos/1643409/pexels-photo-1643409.jpeg",
    "tornado":      "https://images.pexels.com/photos/1162251/pexels-photo-1162251.jpeg",
    "night_clear":  "https://images.pexels.com/photos/813269/pexels-photo-813269.jpeg",
    "night_cloudy": "https://images.pexels.com/photos/531767/pexels-photo-531767.jpeg",
    "extreme_heat": "https://images.pexels.com/photos/1019472/pexels-photo-1019472.jpeg",
    "hot_sunny":    "https://images.pexels.com/photos/301599/pexels-photo-301599.jpeg",
    "warm_clear":   "https://images.pexels.com/photos/8284762/pexels-photo-8284762.jpeg",
    "cloudy":       "https://images.pexels.com/photos/158163/clouds-cloudscape-fluffy-weather-158163.jpeg",
    "partly_cloudy":"https://images.pexels.com/photos/2114014/pexels-photo-2114014.jpeg",
    "cold":         "https://images.pexels.com/photos/1366919/pexels-photo-1366919.jpeg",
    "default":      "https://images.pexels.com/photos/8284762/pexels-photo-8284762.jpeg",
}

def pick_bg(temp, condition):
    hour  = now_ist().hour
    cond  = condition.lower()
    night = hour >= 20 or hour < 5

    if "thunderstorm" in cond:
        return BG_IMAGES["thunderstorm"]
    if "tornado" in cond:
        return BG_IMAGES["tornado"]
    if "snow" in cond or "sleet" in cond or "blizzard" in cond:
        return BG_IMAGES["snow"]
    if "rain" in cond:
        return BG_IMAGES["rain_night"] if night else BG_IMAGES["rain_day"]
    if "drizzle" in cond:
        return BG_IMAGES["drizzle"]
    if "mist" in cond or "fog" in cond:
        return BG_IMAGES["fog"]
    if "haze" in cond:
        return BG_IMAGES["haze"]
    if "smoke" in cond or "ash" in cond:
        return BG_IMAGES["smoke"]
    if "dust" in cond or "sand" in cond:
        return BG_IMAGES["dust"]
    if night:
        return BG_IMAGES["night_clear"] if "clear" in cond else BG_IMAGES["night_cloudy"]
    # Day based on temperature
    if "overcast" in cond or "clouds" in cond:
        return BG_IMAGES["cloudy"]
    if "few clouds" in cond or "scattered" in cond or "broken" in cond:
        return BG_IMAGES["partly_cloudy"]
    if temp >= 38:
        return BG_IMAGES["extreme_heat"]
    if temp >= 32:
        return BG_IMAGES["hot_sunny"]
    if temp >= 20:
        return BG_IMAGES["warm_clear"]
    if temp <= 5:
        return BG_IMAGES["cold"]
    return BG_IMAGES["default"]

def set_bg(temp, condition):
    img = pick_bg(temp, condition)
    st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("{img}");
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
    }}
    [data-testid="stAppViewContainer"] {{
        background-color: rgba(5,10,20,0.72);
    }}
    h1,h2,h3,h4,h5,h6,p,label,span,div {{ color: white; }}
    </style>
    """, unsafe_allow_html=True)

# =============================================================
# DATABASE
# =============================================================

def create_table():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS weather_data (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            city        VARCHAR(80),
            country     VARCHAR(80),
            temperature FLOAT,
            feels_like  FLOAT,
            humidity    INT,
            wind        FLOAT,
            pressure    INT,
            visibility  INT,
            uv_index    FLOAT,
            `condition` VARCHAR(120),
            recorded_at DATETIME
        )
        """))

def should_insert(city, country, minutes=1):
    with engine.connect() as conn:
        last = conn.execute(text("""
            SELECT MAX(recorded_at) FROM weather_data
            WHERE city=:c AND country=:co
        """), {"c": city, "co": country}).scalar()
    if last is None:
        return True
    return (now_ist() - last).total_seconds() / 60 >= minutes

def insert_weather(data):
    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO weather_data
          (city,country,temperature,feels_like,humidity,wind,
           pressure,visibility,uv_index,`condition`,recorded_at)
        VALUES
          (:city,:country,:temperature,:feels_like,:humidity,:wind,
           :pressure,:visibility,:uv_index,:condition,:recorded_at)
        """), data)

def seed_past_data(city, country, country_code):
    with engine.connect() as conn:
        count = conn.execute(text(
            "SELECT COUNT(*) FROM weather_data WHERE city=:c AND country=:co"
        ), {"c": city, "co": country}).scalar()
    if count > 5:
        return
    w = fetch_current(city, country_code)
    if not w:
        return
    rng = np.random.default_rng(42)
    with engine.begin() as conn:
        for days_ago in range(7, 0, -1):
            for hour in [0, 3, 6, 9, 12, 15, 18, 21]:
                ts = now_ist() - timedelta(days=days_ago) + timedelta(
                    hours=hour - now_ist().hour)
                conn.execute(text("""
                    INSERT INTO weather_data
                      (city,country,temperature,feels_like,humidity,wind,
                       pressure,visibility,uv_index,`condition`,recorded_at)
                    VALUES
                      (:city,:country,:temperature,:feels_like,:humidity,:wind,
                       :pressure,:visibility,:uv_index,:condition,:recorded_at)
                """), {
                    "city":        city,
                    "country":     country,
                    "temperature": round(w["temperature"] + rng.uniform(-4, 4), 1),
                    "feels_like":  round(w["feels_like"]  + rng.uniform(-3, 3), 1),
                    "humidity":    int(np.clip(w["humidity"] + rng.integers(-12, 12), 10, 100)),
                    "wind":        round(max(0, w["wind"] + rng.uniform(-1.5, 1.5)), 1),
                    "pressure":    int(w["pressure"] + rng.integers(-6, 6)),
                    "visibility":  w["visibility"],
                    "uv_index":    0.0,
                    "condition":   w["condition"],
                    "recorded_at": ts
                })

@st.cache_data(ttl=60)
def load_history(city, country, limit=300):
    df = pd.read_sql(
        text("""
        SELECT recorded_at,temperature,feels_like,humidity,wind,
               pressure,visibility,`condition`
        FROM weather_data
        WHERE city=:c AND country=:co
        ORDER BY recorded_at DESC LIMIT :l
        """),
        engine, params={"c": city, "co": country, "l": limit}
    )
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    return df.sort_values("recorded_at").reset_index(drop=True)

@st.cache_data(ttl=60)
def load_today(city, country):
    # Use DATE() comparison against IST date
    today_ist = now_ist().date()
    df = pd.read_sql(
        text("""
        SELECT recorded_at,temperature,feels_like,humidity,wind,
               pressure,`condition`
        FROM weather_data
        WHERE city=:c AND country=:co AND DATE(recorded_at)=:d
        ORDER BY recorded_at
        """),
        engine, params={"c": city, "co": country, "d": str(today_ist)}
    )
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    return df

@st.cache_data(ttl=300)
def load_daily_avg(city, country, days=7):
    df = pd.read_sql(
        text("""
        SELECT DATE(recorded_at) AS day,
               ROUND(AVG(temperature),1) AS avg_temp,
               ROUND(AVG(humidity),0)    AS avg_hum,
               ROUND(AVG(wind),1)        AS avg_wind
        FROM weather_data
        WHERE city=:c AND country=:co AND DATE(recorded_at) < :today
        GROUP BY DATE(recorded_at)
        ORDER BY day DESC LIMIT :d
        """),
        engine, params={"c": city, "co": country,
                        "d": days, "today": str(now_ist().date())}
    )
    return df

# =============================================================
# API
# =============================================================

def fetch_current(city, country_code):
    try:
        r = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city},{country_code}&appid={API_KEY}&units=metric", timeout=10
        ).json()
    except Exception:
        return None
    if r.get("cod") != 200:
        return None
    return {
        "city":        city,
        "country":     None,
        "temperature": r["main"]["temp"],
        "feels_like":  r["main"]["feels_like"],
        "humidity":    r["main"]["humidity"],
        "wind":        r["wind"]["speed"],
        "pressure":    r["main"]["pressure"],
        "visibility":  r.get("visibility", 0),
        "uv_index":    0.0,
        "condition":   r["weather"][0]["description"],
        "recorded_at": now_ist()
    }

@st.cache_data(ttl=1800)
def fetch_forecast(city, country_code):
    try:
        r = requests.get(
            f"https://api.openweathermap.org/data/2.5/forecast"
            f"?q={city},{country_code}&appid={API_KEY}&units=metric", timeout=10
        ).json()
    except Exception:
        return pd.DataFrame()
    rows = []
    for item in r.get("list", []):
        # Convert UTC timestamp → IST
        ist_time = datetime.fromtimestamp(item["dt"], tz=timezone.utc).astimezone(IST).replace(tzinfo=None)
        rows.append({
            "time":       ist_time,
            "temp":       item["main"]["temp"],
            "feels_like": item["main"]["feels_like"],
            "humidity":   item["main"]["humidity"],
            "wind":       item["wind"]["speed"],
            "condition":  item["weather"][0]["description"]
        })
    return pd.DataFrame(rows)

# =============================================================
# HELPERS
# =============================================================

def delta_str(cur, prev):
    if prev is None: return None
    d = round(cur - prev, 1)
    return f"{'↑' if d>0 else '↓' if d<0 else '→'} {abs(d)}"

def weather_icon(temp):
    if temp >= 38:   return "🔥"
    elif temp >= 33: return "☀️"
    elif temp >= 28: return "🌤️"
    elif temp >= 20: return "⛅"
    elif temp >= 10: return "🌥️"
    else:            return "❄️"

def city_status(df):
    if len(df) < 3: return ("🟢", "Stable")
    diff = df["temperature"].max() - df["temperature"].min()
    if diff < 1.5:  return ("🟢", "Stable")
    elif diff < 4:  return ("🟡", "Fluctuating")
    else:           return ("🔴", "Volatile")

def comfort_index(temp, humidity):
    hi = temp - 0.55 * (1 - humidity/100) * (temp - 14.5)
    if hi >= 40:   return "🥵 Very Hot"
    elif hi >= 32: return "🌡️ Hot"
    elif hi >= 24: return "😊 Comfortable"
    elif hi >= 16: return "🧥 Cool"
    else:          return "🥶 Cold"

def heat_color(temp):
    if temp >= 35:   return ACCENT6   # rose
    elif temp >= 28: return ACCENT2   # orange
    elif temp >= 20: return ACCENT5   # green
    else:            return ACCENT1   # blue

def apply_time_filter(df, col, option):
    df = df.copy()
    now = now_ist()
    if option == "Last 24h":
        return df[df[col] >= now - timedelta(hours=24)]
    elif option == "Last 3 Days":
        return df[df[col] >= now - timedelta(days=3)]
    elif option == "Last 7 Days":
        return df[df[col] >= now - timedelta(days=7)]
    elif "Night" in option:
        return df[df[col].dt.hour.between(0, 5)]
    elif "Morning" in option:
        return df[df[col].dt.hour.between(6, 11)]
    elif "Afternoon" in option:
        return df[df[col].dt.hour.between(12, 17)]
    elif "Evening" in option:
        return df[df[col].dt.hour.between(18, 23)]
    return df

# =============================================================
# SIDEBAR
# =============================================================

with st.sidebar:
    st.markdown("## ⚙️ Controls")
    st.markdown("---")
    COUNTRY      = st.selectbox("🌍 Country", list(COUNTRY_CITY.keys()))
    CITY         = st.selectbox("🏙️ City",    COUNTRY_CITY[COUNTRY]["cities"])
    COUNTRY_CODE = COUNTRY_CITY[COUNTRY]["code"]
    st.markdown("---")
    TIME_FILTER  = st.selectbox("🕒 Time Filter", [
        "All","Last 24h","Last 3 Days","Last 7 Days",
        "Night (0-5)","Morning (6-11)","Afternoon (12-17)","Evening (18-23)"
    ])
    st.markdown("---")
    COMPARE = st.multiselect(
        "🔀 Compare Cities",
        [c for c in COUNTRY_CITY[COUNTRY]["cities"] if c != CITY],
        default=[]
    )
    st.markdown("---")
    # Refresh options: 1 min + 5/10/30 min
    REFRESH = st.selectbox(
        "🔁 Auto Refresh Interval",
        [1, 5, 10, 30],
        format_func=lambda x: f"Every {x} min{'s' if x > 1 else ''}"
    )
    st.markdown("---")
    st.markdown(f"**📍 {CITY}, {COUNTRY}**")
    st.caption(f"🕒 IST: {now_ist().strftime('%d %b %Y  %H:%M:%S')}")

# =============================================================
# AUTO REFRESH  (in milliseconds)
# =============================================================

st_autorefresh(interval=REFRESH * 60 * 1000, key="autorefresh")

# =============================================================
# BOOT — fetch, seed, store
# =============================================================

create_table()
current = fetch_current(CITY, COUNTRY_CODE)
if not current:
    st.error("❌ Could not fetch weather. Check city/API key.")
    st.stop()

current["country"] = COUNTRY
seed_past_data(CITY, COUNTRY, COUNTRY_CODE)

# Always try to insert every 1 minute regardless of display refresh
if should_insert(CITY, COUNTRY, minutes=1):
    insert_weather(current)

set_bg(current["temperature"], current["condition"])

forecast_df   = fetch_forecast(CITY, COUNTRY_CODE)
history_df    = load_history(CITY, COUNTRY)
today_df      = load_today(CITY, COUNTRY)
daily_df      = load_daily_avg(CITY, COUNTRY)

hist_filtered  = apply_time_filter(history_df, "recorded_at", TIME_FILTER)
today_filtered = apply_time_filter(today_df,   "recorded_at", TIME_FILTER)

# =============================================================
# HEADER
# =============================================================

st.markdown("# 🌦️ Weather Analytics Pro")
st.caption(
    f"📍 {CITY}, {COUNTRY}  ·  "
    f"🕒 IST: {now_ist().strftime('%A, %d %B %Y  %H:%M')}  ·  "
    f"🔁 Data collected every 1 min  ·  Display refresh every {REFRESH} min"
)
st.divider()

# =============================================================
# TABS
# =============================================================

tab_home, tab_data, tab_graphs, tab_compare, tab_forecast, tab_tour = st.tabs([
    "🏠 Overview", "📊 Data", "📈 Graphs", "🏙️ Compare", "🔮 Forecast", "📖 Walkthrough"
])

# ─────────────────────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ─────────────────────────────────────────────────────────────

with tab_home:
    prev   = today_df.iloc[-2] if len(today_df) > 1 else None
    s_icon, s_label = city_status(today_df)

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric(f"{weather_icon(current['temperature'])} Temperature",
              f"{current['temperature']}°C",
              delta_str(current["temperature"],
                        prev["temperature"] if prev is not None else None))
    c2.metric("🌡️ Feels Like",  f"{current['feels_like']}°C")
    c3.metric("💧 Humidity",    f"{current['humidity']}%")
    c4.metric("🌬️ Wind",        f"{current['wind']} m/s")
    c5.metric("🔵 Pressure",    f"{current['pressure']} hPa")
    c6.metric(f"{s_icon} Status", s_label)

    comfort = comfort_index(current["temperature"], current["humidity"])
    vis_km  = round(current["visibility"]/1000, 1) if current["visibility"] else "N/A"
    st.markdown(f"""
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin:14px 0 22px;">
        <div class="badge" style="background:rgba(56,189,248,0.15);color:#38bdf8;border:1px solid rgba(56,189,248,0.3);">
            ☁️ {current['condition'].title()}</div>
        <div class="badge" style="background:rgba(34,211,238,0.15);color:#22d3ee;border:1px solid rgba(34,211,238,0.3);">
            {comfort}</div>
        <div class="badge" style="background:rgba(249,115,22,0.15);color:#f97316;border:1px solid rgba(249,115,22,0.3);">
            👁️ Visibility: {vis_km} km</div>
        <div class="badge" style="background:rgba(167,139,250,0.15);color:#a78bfa;border:1px solid rgba(167,139,250,0.3);">
            🕒 Updated: {now_ist().strftime('%H:%M IST')}</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Alerts
    cond_l = current["condition"].lower()
    if current["temperature"] >= 38:
        st.warning("🔥 **Extreme Heat Alert** — Stay hydrated & avoid direct sun.", icon="⚠️")
    if "rain" in cond_l or "thunderstorm" in cond_l:
        st.info("🌧️ **Rain / Storm detected** — Carry an umbrella.", icon="ℹ️")
    if current["wind"] >= 10:
        st.warning("💨 **High Wind Advisory** — Wind speed above 10 m/s.", icon="⚠️")
    if "snow" in cond_l or "blizzard" in cond_l:
        st.info("❄️ **Snow conditions** — Roads may be slippery.", icon="ℹ️")

    if not daily_df.empty:
        st.subheader("📅 Past Days Average")
        cols = st.columns(min(len(daily_df), 7))
        for col, (_, row) in zip(cols, daily_df.iterrows()):
            col.markdown(f"""
            <div class="wcard">
                <div class="label">{pd.to_datetime(row['day']).strftime('%a %d')}</div>
                <div class="icon">{weather_icon(row['avg_temp'])}</div>
                <div class="temp">{row['avg_temp']}°C</div>
                <div class="sub">💧{int(row['avg_hum'])}% 🌬️{row['avg_wind']}m/s</div>
            </div>""", unsafe_allow_html=True)

    st.divider()

    if not forecast_df.empty:
        st.subheader("🔮 5-Day Forecast")
        fdf = forecast_df.copy()
        fdf["day"] = fdf["time"].dt.date
        daily_fc = (
            fdf[fdf["day"] > now_ist().date()]
            .groupby("day")
            .agg(avg_temp=("temp","mean"), avg_hum=("humidity","mean"),
                 avg_wind=("wind","mean"), condition=("condition","first"))
            .round(1).reset_index().head(5)
        )
        cols = st.columns(len(daily_fc))
        for col, (_, row) in zip(cols, daily_fc.iterrows()):
            col.markdown(f"""
            <div class="wcard">
                <div class="label">{pd.to_datetime(row['day']).strftime('%A')}</div>
                <div class="icon">{weather_icon(row['avg_temp'])}</div>
                <div class="temp">{row['avg_temp']}°C</div>
                <div class="sub">{row['condition'].title()}</div>
                <div class="sub">💧{int(row['avg_hum'])}%</div>
            </div>""", unsafe_allow_html=True)

    st.divider()

    if not today_df.empty:
        st.subheader("📊 Today's Quick Stats (IST)")
        t = today_df["temperature"]
        a,b,c,d = st.columns(4)
        a.metric("🌡️ Max",   f"{t.max():.1f}°C")
        b.metric("❄️ Min",   f"{t.min():.1f}°C")
        c.metric("📊 Avg",   f"{t.mean():.1f}°C")
        d.metric("📏 Range", f"{(t.max()-t.min()):.1f}°C")

# ─────────────────────────────────────────────────────────────
# TAB 2 — DATA
# ─────────────────────────────────────────────────────────────

with tab_data:
    st1, st2, st3 = st.tabs(["🔴 Today Live", "🕰️ History", "📅 Daily Avg"])

    with st1:
        st.subheader(f"Today's Readings — {CITY}  (IST)")
        if today_filtered.empty:
            st.warning("No data for selected time filter.")
        else:
            d = today_filtered.copy()
            d["recorded_at"] = d["recorded_at"].dt.strftime("%d %b %Y  %H:%M IST")
            d = d.rename(columns={
                "recorded_at":"Recorded At (IST)","temperature":"Temp (°C)",
                "feels_like":"Feels Like (°C)","humidity":"Humidity (%)",
                "wind":"Wind (m/s)","pressure":"Pressure (hPa)","condition":"Condition"
            })
            st.dataframe(d, use_container_width=True, height=420)
            st.download_button("⬇️ Download CSV", d.to_csv(index=False),
                               f"{CITY}_today.csv", "text/csv")

    with st2:
        st.subheader(f"Full History — {CITY}  ({TIME_FILTER})  (IST)")
        if hist_filtered.empty:
            st.warning("No data for selected time filter.")
        else:
            d = hist_filtered.copy()
            d["recorded_at"] = d["recorded_at"].dt.strftime("%d %b %Y  %H:%M IST")
            d = d.rename(columns={
                "recorded_at":"Recorded At (IST)","temperature":"Temp (°C)",
                "feels_like":"Feels Like (°C)","humidity":"Humidity (%)",
                "wind":"Wind (m/s)","pressure":"Pressure (hPa)","condition":"Condition"
            })
            st.dataframe(d, use_container_width=True, height=420)
            st.download_button("⬇️ Download CSV", d.to_csv(index=False),
                               f"{CITY}_history.csv", "text/csv")

    with st3:
        st.subheader(f"Daily Averages — {CITY}")
        if daily_df.empty:
            st.info("Collecting data…")
        else:
            st.dataframe(daily_df, use_container_width=True)

# ─────────────────────────────────────────────────────────────
# TAB 3 — GRAPHS  (enhanced, ECharts-inspired style)
# ─────────────────────────────────────────────────────────────

with tab_graphs:

    if hist_filtered.empty:
        st.warning(
            "⚠️ No data for the selected time range. "
            "Change the time filter or wait for more data."
        )
    else:
        x   = hist_filtered["recorded_at"]
        FMT = mdates.DateFormatter("%d-%b %H:%M")

        # ═══════════════════════════════════════════════
        # GRAPH 1 — Smooth Multi-line (Temp/Humidity/Wind)
        # ═══════════════════════════════════════════════
        st.markdown('<div class="graph-label">📈 Graph 1 — Temperature, Humidity & Wind Trends</div>',
                    unsafe_allow_html=True)

        fig1, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
        fig1.patch.set_facecolor(DARK_BG)
        fig1.subplots_adjust(hspace=0.08, top=0.96, bottom=0.08)

        metrics = [
            ("temperature", "°C",   ACCENT1),
            ("humidity",    "%",    ACCENT5),
            ("wind",        "m/s",  ACCENT2),
        ]
        for ax, (col, unit, color) in zip(axes, metrics):
            y = hist_filtered[col].values
            xs = np.arange(len(x))
            ax.set_facecolor(CARD_BG2)
            # Gradient fill
            ax.fill_between(x, y, y.min() * 0.95, color=color, alpha=0.18, zorder=2)
            ax.plot(x, y, color=color, linewidth=2.2, zorder=3, solid_capstyle="round")
            # Max/Min dots
            imax, imin = int(np.argmax(y)), int(np.argmin(y))
            ax.scatter(x.iloc[imax], y[imax], color="#ff4d6d", s=80, zorder=6,
                       edgecolors="white", linewidths=1.2)
            ax.scatter(x.iloc[imin], y[imin], color="#00cfde", s=80, zorder=6,
                       edgecolors="white", linewidths=1.2)
            ax.annotate(f"{y[imax]:.1f}{unit}", (x.iloc[imax], y[imax]),
                        xytext=(0,9), textcoords="offset points",
                        ha="center", fontsize=9, color="#ff4d6d", fontweight="bold")
            ax.annotate(f"{y[imin]:.1f}{unit}", (x.iloc[imin], y[imin]),
                        xytext=(0,-14), textcoords="offset points",
                        ha="center", fontsize=9, color="#00cfde", fontweight="bold")
            # Avg line
            ax.axhline(y.mean(), color="white", linestyle=":", linewidth=1.1, alpha=0.4)
            ax.set_ylabel(f"{col.title()} ({unit})", color=TEXT_COL, fontsize=9)
            for spine in ax.spines.values():
                spine.set_edgecolor(GRID_COL)
            ax.grid(True, linestyle="--", alpha=0.2, color=GRID_COL)
            ax.tick_params(colors=TEXT_COL, labelsize=8)
            ax.yaxis.label.set_color(TEXT_COL)

        axes[-1].xaxis.set_major_formatter(FMT)
        plt.xticks(rotation=30, ha="right", color=TEXT_COL, fontsize=8)
        fig1.suptitle(f"Weather Metrics Trend — {CITY}, {COUNTRY}",
                      color=TEXT_COL, fontsize=14, fontweight="bold", y=0.99)
        st.pyplot(fig1)
        plt.close(fig1)

        st.divider()

        # ═══════════════════════════════════════════════
        # GRAPH 2 — Today's Temperature with gradient area
        # ═══════════════════════════════════════════════
        st.markdown('<div class="graph-label">⚡ Graph 2 — Today\'s Live Temperature (IST)</div>',
                    unsafe_allow_html=True)

        if today_filtered.empty:
            st.info("No today data for this time filter.")
        else:
            xt = today_filtered["recorded_at"]
            yt = today_filtered["temperature"]

            fig2, ax2 = plt.subplots(figsize=(14, 5))
            style_ax(ax2, fig2, f"Today's Temperature — {CITY} (IST)")

            ax2.plot(xt, yt, color=ACCENT2, linewidth=2.8,
                     marker="o", markersize=5,
                     markerfacecolor="white", markeredgecolor=ACCENT2, zorder=4)
            ax2.fill_between(xt, yt, yt.min() - 0.5, color=ACCENT2, alpha=0.15)

            if len(yt) >= 3:
                roll = yt.rolling(3, min_periods=1).mean()
                ax2.plot(xt, roll, color="white", linewidth=1.4,
                         linestyle="--", alpha=0.5, label="3-pt Avg")

            imax, imin = yt.argmax(), yt.argmin()
            ax2.scatter(xt.iloc[imax], yt.max(), color="#ff4d6d", s=130, zorder=6,
                        edgecolors="white", linewidths=1.5)
            ax2.scatter(xt.iloc[imin], yt.min(), color="#00cfde", s=130, zorder=6,
                        edgecolors="white", linewidths=1.5)
            ax2.annotate(f"Max {yt.max():.1f}°C",
                         (xt.iloc[imax], yt.max()), xytext=(0,13),
                         textcoords="offset points", ha="center",
                         fontsize=10, fontweight="bold", color="#ff4d6d")
            ax2.annotate(f"Min {yt.min():.1f}°C",
                         (xt.iloc[imin], yt.min()), xytext=(0,-17),
                         textcoords="offset points", ha="center",
                         fontsize=10, fontweight="bold", color="#00cfde")

            ax2.set_ylabel("Temperature (°C)", color=TEXT_COL)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M IST"))
            plt.xticks(rotation=30, ha="right", color=TEXT_COL, fontsize=8)
            ax2.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9,
                       framealpha=0.6, edgecolor=GRID_COL)
            plt.tight_layout()
            st.pyplot(fig2)
            plt.close(fig2)

        st.divider()

        # ═══════════════════════════════════════════════
        # GRAPH 3 — Dual-axis: Temp line + Humidity area bars
        # ═══════════════════════════════════════════════
        st.markdown('<div class="graph-label">📊 Graph 3 — Temperature vs Humidity (Dual Axis)</div>',
                    unsafe_allow_html=True)

        fig3, ax3 = plt.subplots(figsize=(14, 5))
        style_ax(ax3, fig3, f"Temperature vs Humidity — {CITY}")

        ax3.plot(x, hist_filtered["temperature"], color=ACCENT1,
                 linewidth=2.5, label="Temp (°C)", zorder=3)
        ax3.fill_between(x, hist_filtered["temperature"],
                         hist_filtered["temperature"].min(),
                         color=ACCENT1, alpha=0.12)
        ax3.set_ylabel("Temperature (°C)", color=ACCENT1, fontsize=10)
        ax3.tick_params(axis="y", colors=ACCENT1)

        ax3b = ax3.twinx()
        ax3b.bar(x, hist_filtered["humidity"], color=ACCENT5,
                 alpha=0.32, label="Humidity (%)", width=0.012)
        ax3b.set_ylabel("Humidity (%)", color=ACCENT5, fontsize=10)
        ax3b.tick_params(axis="y", colors=ACCENT5)
        ax3b.set_facecolor(CARD_BG2)
        ax3b.grid(False)
        for spine in ax3b.spines.values():
            spine.set_edgecolor(GRID_COL)

        l1, lb1 = ax3.get_legend_handles_labels()
        l2, lb2 = ax3b.get_legend_handles_labels()
        ax3.legend(l1+l2, lb1+lb2, facecolor=CARD_BG, labelcolor=TEXT_COL,
                   fontsize=9, framealpha=0.7, edgecolor=GRID_COL)
        ax3.xaxis.set_major_formatter(FMT)
        plt.xticks(rotation=30, ha="right", color=TEXT_COL, fontsize=8)
        plt.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)

        st.divider()

        # ═══════════════════════════════════════════════
        # GRAPH 4 — Heatmap: Hour × Day (ECharts style)
        # ═══════════════════════════════════════════════
        st.markdown('<div class="graph-label">🌡️ Graph 4 — Hourly Temperature Heatmap (Hour × Day)</div>',
                    unsafe_allow_html=True)

        hm = history_df.copy()
        hm["hour"] = hm["recorded_at"].dt.hour
        hm["date"] = hm["recorded_at"].dt.date
        pivot = hm.pivot_table(values="temperature",
                               index="hour", columns="date", aggfunc="mean")

        if pivot.empty:
            st.info("Not enough data for heatmap yet.")
        else:
            fig4, ax4 = plt.subplots(figsize=(14, 6))
            fig4.patch.set_facecolor(DARK_BG)
            ax4.set_facecolor(DARK_BG)

            im = ax4.imshow(pivot.values, aspect="auto",
                            cmap="YlOrRd", interpolation="nearest",
                            vmin=pivot.values.min(), vmax=pivot.values.max())
            cbar4 = plt.colorbar(im, ax=ax4, fraction=0.03, pad=0.02)
            cbar4.set_label("°C", color=TEXT_COL, fontsize=10)
            cbar4.ax.yaxis.set_tick_params(color=TEXT_COL)
            plt.setp(plt.getp(cbar4.ax.axes, "yticklabels"), color=TEXT_COL)

            # Add value annotations
            for i in range(pivot.values.shape[0]):
                for j in range(pivot.values.shape[1]):
                    v = pivot.values[i, j]
                    if not np.isnan(v):
                        ax4.text(j, i, f"{v:.0f}", ha="center", va="center",
                                 fontsize=7, color="white" if v > pivot.values.mean() else DARK_BG,
                                 fontweight="bold")

            ax4.set_xticks(range(len(pivot.columns)))
            ax4.set_xticklabels([str(d) for d in pivot.columns],
                                rotation=45, ha="right", fontsize=8, color=TEXT_COL)
            ax4.set_yticks(range(len(pivot.index)))
            ax4.set_yticklabels([f"{h:02d}:00" for h in pivot.index],
                                fontsize=8, color=TEXT_COL)
            ax4.set_title(f"Hourly Temperature Heatmap — {CITY} (IST)",
                          color=TEXT_COL, fontweight="bold", fontsize=13, pad=12)
            for spine in ax4.spines.values():
                spine.set_edgecolor(GRID_COL)
            plt.tight_layout()
            st.pyplot(fig4)
            plt.close(fig4)

        st.divider()

        # ═══════════════════════════════════════════════
        # GRAPH 5 — Wind Bars (colour-graded, styled)
        # ═══════════════════════════════════════════════
        st.markdown('<div class="graph-label">🌬️ Graph 5 — Wind Speed History (Colour-graded Bars)</div>',
                    unsafe_allow_html=True)

        fig5, ax5 = plt.subplots(figsize=(14, 4))
        style_ax(ax5, fig5, f"Wind Speed — {CITY}")

        wind_vals  = hist_filtered["wind"].values
        wind_times = hist_filtered["recorded_at"].values
        wmin, wmax = wind_vals.min(), wind_vals.max()
        wind_norm  = (wind_vals - wmin) / (np.ptp(wind_vals) + 1e-6)
        cmap_wind  = plt.cm.YlOrRd

        bars5 = ax5.bar(wind_times, wind_vals,
                        color=[cmap_wind(v) for v in wind_norm],
                        width=np.timedelta64(28, "m"), zorder=3,
                        linewidth=0, edgecolor="none")

        # Threshold line
        ax5.axhline(wind_vals.mean(), color="white", linewidth=1.2,
                    linestyle="--", alpha=0.5, label=f"Avg {wind_vals.mean():.1f} m/s")
        ax5.set_ylabel("Wind Speed (m/s)", color=TEXT_COL, fontsize=10)
        ax5.xaxis.set_major_formatter(FMT)
        plt.xticks(rotation=30, ha="right", color=TEXT_COL, fontsize=8)
        ax5.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9,
                   framealpha=0.6, edgecolor=GRID_COL)

        sm5 = plt.cm.ScalarMappable(cmap=cmap_wind,
                                     norm=plt.Normalize(wmin, wmax))
        sm5.set_array([])
        cbar5 = plt.colorbar(sm5, ax=ax5, pad=0.01, fraction=0.025)
        cbar5.set_label("m/s", color=TEXT_COL)
        cbar5.ax.yaxis.set_tick_params(color=TEXT_COL)
        plt.setp(plt.getp(cbar5.ax.axes, "yticklabels"), color=TEXT_COL)
        plt.tight_layout()
        st.pyplot(fig5)
        plt.close(fig5)

        st.divider()

        # ═══════════════════════════════════════════════
        # GRAPH 6 — Scatter: Temp vs Humidity (bubble chart)
        # ═══════════════════════════════════════════════
        st.markdown('<div class="graph-label">🔵 Graph 6 — Temperature vs Humidity Scatter (Wind = Size & Colour)</div>',
                    unsafe_allow_html=True)

        fig6, ax6 = plt.subplots(figsize=(10, 5))
        style_ax(ax6, fig6, f"Temp vs Humidity — {CITY}")

        sc_x = hist_filtered["temperature"]
        sc_y = hist_filtered["humidity"]
        sc_c = hist_filtered["wind"]
        sc_s = (sc_c - sc_c.min() + 0.5) / (sc_c.max() - sc_c.min() + 0.5) * 200 + 30

        sc = ax6.scatter(sc_x, sc_y, c=sc_c, cmap="cool",
                         s=sc_s, alpha=0.7,
                         edgecolors=GRID_COL, linewidths=0.4, zorder=3)
        cbar6 = plt.colorbar(sc, ax=ax6, pad=0.02, fraction=0.03)
        cbar6.set_label("Wind (m/s)", color=TEXT_COL)
        cbar6.ax.yaxis.set_tick_params(color=TEXT_COL)
        plt.setp(plt.getp(cbar6.ax.axes, "yticklabels"), color=TEXT_COL)

        if len(sc_x) > 3:
            z  = np.polyfit(sc_x, sc_y, 1)
            p  = np.poly1d(z)
            xs = np.linspace(sc_x.min(), sc_x.max(), 100)
            ax6.plot(xs, p(xs), color="white", linewidth=1.8,
                     linestyle="--", alpha=0.55, label="Trend")
            ax6.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9,
                       framealpha=0.6, edgecolor=GRID_COL)

        ax6.set_xlabel("Temperature (°C)", color=TEXT_COL, fontsize=10)
        ax6.set_ylabel("Humidity (%)",     color=TEXT_COL, fontsize=10)
        plt.tight_layout()
        st.pyplot(fig6)
        plt.close(fig6)

        st.divider()

        # ═══════════════════════════════════════════════
        # GRAPH 7 — Daily Avg Bar Chart (styled like ECharts)
        # ═══════════════════════════════════════════════
        st.markdown('<div class="graph-label">📅 Graph 7 — Daily Average Temperature (Past Week)</div>',
                    unsafe_allow_html=True)

        if daily_df.empty:
            st.info("Daily averages appear after at least one full day of data.")
        else:
            daily_plot = daily_df.sort_values("day")
            day_labels = [pd.to_datetime(d).strftime("%a\n%d %b")
                          for d in daily_plot["day"]]
            day_temps  = daily_plot["avg_temp"].values
            day_hums   = daily_plot["avg_hum"].values

            fig7, ax7 = plt.subplots(figsize=(12, 5))
            style_ax(ax7, fig7, f"Daily Avg Temperature & Humidity — {CITY}")

            x7 = np.arange(len(day_labels))
            width = 0.4

            bars_t = ax7.bar(x7 - width/2, day_temps,
                             color=[heat_color(t) for t in day_temps],
                             width=width, zorder=3, linewidth=0,
                             label="Avg Temp (°C)")
            ax7b = ax7.twinx()
            bars_h = ax7b.bar(x7 + width/2, day_hums,
                              color=ACCENT5, alpha=0.45,
                              width=width, zorder=3, linewidth=0,
                              label="Avg Humidity (%)")
            ax7b.set_ylabel("Humidity (%)", color=ACCENT5, fontsize=10)
            ax7b.tick_params(axis="y", colors=ACCENT5, labelsize=8)
            ax7b.grid(False)
            for spine in ax7b.spines.values():
                spine.set_edgecolor(GRID_COL)

            for bar, temp in zip(bars_t, day_temps):
                ax7.text(bar.get_x() + bar.get_width()/2,
                         bar.get_height() + 0.2,
                         f"{temp}°C",
                         ha="center", va="bottom",
                         fontsize=10, fontweight="bold", color=TEXT_COL)

            avg_line = day_temps.mean()
            ax7.axhline(avg_line, color="white", linewidth=1.3,
                        linestyle="--", alpha=0.5,
                        label=f"Week Avg: {avg_line:.1f}°C")

            ax7.set_xticks(x7)
            ax7.set_xticklabels(day_labels, color=TEXT_COL, fontsize=9)
            ax7.set_ylabel("Temperature (°C)", color=TEXT_COL, fontsize=10)
            ax7.set_ylim(0, day_temps.max() + 6)

            lines1, labels1 = ax7.get_legend_handles_labels()
            lines2, labels2 = ax7b.get_legend_handles_labels()
            ax7.legend(lines1+lines2, labels1+labels2,
                       facecolor=CARD_BG, labelcolor=TEXT_COL,
                       fontsize=9, framealpha=0.7, edgecolor=GRID_COL)
            plt.tight_layout()
            st.pyplot(fig7)
            plt.close(fig7)

        st.divider()

        # ═══════════════════════════════════════════════
        # GRAPH 8 — Pressure trend (bonus)
        # ═══════════════════════════════════════════════
        st.markdown('<div class="graph-label">🔷 Graph 8 — Atmospheric Pressure Trend</div>',
                    unsafe_allow_html=True)

        fig8, ax8 = plt.subplots(figsize=(14, 4))
        style_ax(ax8, fig8, f"Pressure Trend — {CITY}")
        p_vals = hist_filtered["pressure"]
        ax8.plot(x, p_vals, color=ACCENT4, linewidth=2.2, zorder=3)
        ax8.fill_between(x, p_vals, p_vals.min() - 1, color=ACCENT4, alpha=0.15)
        ax8.axhline(p_vals.mean(), color="white", linewidth=1.1,
                    linestyle=":", alpha=0.5,
                    label=f"Mean {p_vals.mean():.0f} hPa")
        ax8.set_ylabel("Pressure (hPa)", color=TEXT_COL, fontsize=10)
        ax8.xaxis.set_major_formatter(FMT)
        ax8.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9,
                   framealpha=0.6, edgecolor=GRID_COL)
        plt.xticks(rotation=30, ha="right", color=TEXT_COL, fontsize=8)
        plt.tight_layout()
        st.pyplot(fig8)
        plt.close(fig8)

# ─────────────────────────────────────────────────────────────
# TAB 4 — COMPARE
# ─────────────────────────────────────────────────────────────

with tab_compare:
    st.subheader(f"🏙️ City Comparison — {COUNTRY}")

    all_cities = [CITY] + COMPARE
    live_rows  = []
    for c in all_cities:
        w = fetch_current(c, COUNTRY_CODE)
        if w:
            si, sl = city_status(load_today(c, COUNTRY))
            live_rows.append({
                "City":         c,
                "Temp (°C)":    w["temperature"],
                "Feels Like":   w["feels_like"],
                "Humidity (%)": w["humidity"],
                "Wind (m/s)":   w["wind"],
                "Condition":    w["condition"].title(),
                "Status":       f"{si} {sl}"
            })

    if live_rows:
        st.dataframe(pd.DataFrame(live_rows), use_container_width=True, height=250)

    st.divider()

    if COMPARE:
        st.subheader("📈 Temperature Trend Comparison — Today (IST)")
        fig_c, ax_c = plt.subplots(figsize=(14, 5))
        style_ax(ax_c, fig_c, "City Temperature Comparison — Today")

        comp_colors = [ACCENT1, ACCENT2, ACCENT5, ACCENT4, ACCENT3, ACCENT6]
        if not today_df.empty:
            ax_c.plot(today_df["recorded_at"], today_df["temperature"],
                      color=comp_colors[0], linewidth=3,
                      marker="o", markersize=5, label=CITY)

        for i, city in enumerate(COMPARE):
            df_c = load_today(city, COUNTRY)
            if not df_c.empty:
                ax_c.plot(df_c["recorded_at"], df_c["temperature"],
                          color=comp_colors[(i+1) % len(comp_colors)],
                          linewidth=2.5, linestyle="--",
                          marker="s", markersize=4, label=city)

        ax_c.set_ylabel("Temperature (°C)", color=TEXT_COL)
        ax_c.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M IST"))
        plt.xticks(rotation=30, ha="right", color=TEXT_COL, fontsize=8)
        ax_c.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9,
                    framealpha=0.7, edgecolor=GRID_COL)
        plt.tight_layout()
        st.pyplot(fig_c)
        plt.close(fig_c)

        st.divider()

        st.subheader("📊 Current Temperature Bar Chart")
        fig_b, ax_b = plt.subplots(figsize=(10, 4))
        style_ax(ax_b, fig_b, "Live Temperature Comparison")

        bc   = [r["City"] for r in live_rows]
        bt   = [r["Temp (°C)"] for r in live_rows]
        bars = ax_b.bar(bc, bt,
                        color=[heat_color(t) for t in bt],
                        edgecolor="none", linewidth=0,
                        width=0.5, zorder=3)
        for bar, temp in zip(bars, bt):
            ax_b.text(bar.get_x() + bar.get_width()/2,
                      bar.get_height() + 0.2,
                      f"{temp}°C",
                      ha="center", fontsize=10,
                      fontweight="bold", color=TEXT_COL)
        ax_b.set_ylabel("Temperature (°C)", color=TEXT_COL)
        ax_b.tick_params(colors=TEXT_COL)
        plt.tight_layout()
        st.pyplot(fig_b)
        plt.close(fig_b)
    else:
        st.info("👈 Select cities from the sidebar to compare.")

# ─────────────────────────────────────────────────────────────
# TAB 5 — FORECAST
# ─────────────────────────────────────────────────────────────

with tab_forecast:
    st.subheader(f"🔮 5-Day Detailed Forecast — {CITY}  (IST)")

    if forecast_df.empty:
        st.warning("Could not load forecast.")
    else:
        xf = forecast_df["time"]
        yf = forecast_df["temp"]

        fig_f, ax_f = plt.subplots(figsize=(14, 5))
        style_ax(ax_f, fig_f, f"5-Day Forecast — {CITY}, {COUNTRY} (IST)")

        ax_f.plot(xf, yf, color=ACCENT2, linewidth=2.8,
                  marker="o", markersize=5,
                  markerfacecolor="white", markeredgecolor=ACCENT2,
                  label="Forecast Temp", zorder=4)
        ax_f.fill_between(xf, yf-1.5, yf+1.5,
                          color=ACCENT5, alpha=0.15, label="±1.5°C band")
        ax_f.fill_between(xf, yf, yf.min()-1, color=ACCENT2, alpha=0.10)

        mi, ma = yf.idxmin(), yf.idxmax()
        ax_f.scatter(xf[ma], yf.max(), color="#ff4d6d", s=130, zorder=6,
                     edgecolors="white", linewidths=1.5)
        ax_f.scatter(xf[mi], yf.min(), color="#00cfde", s=130, zorder=6,
                     edgecolors="white", linewidths=1.5)
        ax_f.annotate(f"Max {yf.max():.1f}°C", (xf[ma], yf.max()),
                      xytext=(0,14), textcoords="offset points",
                      ha="center", fontsize=10, fontweight="bold", color="#ff4d6d")
        ax_f.annotate(f"Min {yf.min():.1f}°C", (xf[mi], yf.min()),
                      xytext=(0,-18), textcoords="offset points",
                      ha="center", fontsize=10, fontweight="bold", color="#00cfde")

        ax_f.set_xlabel("Date & Time (IST)", color=TEXT_COL)
        ax_f.set_ylabel("Temperature (°C)", color=TEXT_COL)
        ax_f.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
        plt.xticks(rotation=40, ha="right", color=TEXT_COL, fontsize=8)
        ax_f.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9,
                    framealpha=0.7, edgecolor=GRID_COL)
        plt.tight_layout()
        st.pyplot(fig_f)
        plt.close(fig_f)

        st.divider()

        col_h, col_w = st.columns(2)
        with col_h:
            st.subheader("💧 Humidity Forecast")
            fig_h, ax_h = plt.subplots(figsize=(8, 4))
            style_ax(ax_h, fig_h, "Humidity Forecast (IST)")
            ax_h.fill_between(forecast_df["time"], forecast_df["humidity"],
                              color=ACCENT5, alpha=0.40)
            ax_h.plot(forecast_df["time"], forecast_df["humidity"],
                      color=ACCENT5, linewidth=2.2)
            ax_h.set_ylabel("Humidity (%)", color=TEXT_COL)
            ax_h.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            plt.xticks(rotation=35, ha="right", color=TEXT_COL, fontsize=8)
            plt.tight_layout()
            st.pyplot(fig_h)
            plt.close(fig_h)

        with col_w:
            st.subheader("🌬️ Wind Speed Forecast")
            fig_w, ax_w = plt.subplots(figsize=(8, 4))
            style_ax(ax_w, fig_w, "Wind Speed Forecast (IST)")
            ax_w.bar(forecast_df["time"], forecast_df["wind"],
                     color=ACCENT6, alpha=0.8, width=0.04, linewidth=0)
            ax_w.set_ylabel("Wind Speed (m/s)", color=TEXT_COL)
            ax_w.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            plt.xticks(rotation=35, ha="right", color=TEXT_COL, fontsize=8)
            plt.tight_layout()
            st.pyplot(fig_w)
            plt.close(fig_w)

        st.divider()
        st.subheader("📋 Forecast Table (IST)")
        fc_display = forecast_df.copy()
        fc_display["time"] = fc_display["time"].dt.strftime("%d %b %Y  %H:%M IST")
        fc_display = fc_display.rename(columns={
            "time":"Date & Time (IST)","temp":"Temp (°C)",
            "feels_like":"Feels Like (°C)","humidity":"Humidity (%)",
            "wind":"Wind (m/s)","condition":"Condition"
        })
        st.dataframe(fc_display, use_container_width=True, height=380)
        st.download_button("⬇️ Download Forecast CSV",
                           fc_display.to_csv(index=False),
                           f"{CITY}_forecast.csv", "text/csv")

# ─────────────────────────────────────────────────────────────
# TAB 6 — WALKTHROUGH
# ─────────────────────────────────────────────────────────────

with tab_tour:
    st.markdown("""
    <div style="text-align:center;padding:30px 0 10px;">
        <div style="font-size:52px;margin-bottom:12px;">🌦️</div>
        <h1 style="font-size:32px;font-weight:800;margin-bottom:6px;">Welcome to Weather Analytics Pro</h1>
        <p style="font-size:16px;opacity:0.7;max-width:600px;margin:auto;">
            Your real-time weather intelligence dashboard. Here's everything you need to know
            to get the most out of this app.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Quick Start
    st.subheader("🚀 Quick Start in 3 Steps")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="tour-card">
            <div class="tour-step">Step 1</div>
            <div class="tour-title">📍 Pick Your Location</div>
            <div class="tour-desc">Use the <b>Country</b> and <b>City</b> dropdowns in the left sidebar. Each country has 10–15 popular cities to choose from. The dashboard instantly loads live weather for your selection.</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="tour-card">
            <div class="tour-step">Step 2</div>
            <div class="tour-title">⏰ Set Refresh Interval</div>
            <div class="tour-desc">Under <b>Auto Refresh Interval</b> in the sidebar, choose how often the dashboard updates — every 1, 5, 10, or 30 minutes. <b>Data is always collected every 1 minute</b> in the background regardless of display refresh.</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="tour-card">
            <div class="tour-step">Step 3</div>
            <div class="tour-title">🔍 Explore the Tabs</div>
            <div class="tour-desc">Navigate through the five main tabs at the top: Overview, Data, Graphs, Compare, and Forecast. Each tab offers a different perspective on weather intelligence.</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📑 Tab-by-Tab Guide")

    pages = [
        ("🏠", "Overview", ACCENT1,
         "Your weather at a glance. Six live metric cards show Temperature, Feels Like, Humidity, Wind Speed, Pressure, and City Status. Coloured badges indicate the current condition, comfort index, and visibility. Smart alerts appear automatically for extreme heat, rain, high winds, or snow. Scroll down for a 7-day historical card row and a 5-day forecast preview, plus today's quick stats (Max/Min/Avg/Range)."),
        ("📊", "Data", ACCENT5,
         "Raw tabular data in three sub-tabs: Today Live (all readings taken today in IST), History (full record filtered by your selected time window), and Daily Avg (daily aggregates for the past week). Every table has a ⬇️ Download CSV button so you can export data for your own analysis. All timestamps are displayed in IST."),
        ("📈", "Graphs", ACCENT2,
         "Eight professional charts rendered with Matplotlib in a dark ECharts-inspired style. Graph 1 shows stacked multi-line trends for all three core metrics. Graph 2 is today's live temperature with a rolling average. Graph 3 overlays temp and humidity on dual axes. Graph 4 is an hourly heatmap. Graphs 5–8 cover wind bars, bubble scatter correlation, daily bar+humidity combo, and atmospheric pressure trend."),
        ("🏙️", "Compare", ACCENT4,
         "Select one or more additional cities from the <b>Compare Cities</b> multiselect in the sidebar. A live comparison table appears at the top, followed by overlaid temperature trend lines and a side-by-side bar chart of current temperatures. Great for understanding regional weather differences at a glance."),
        ("🔮", "Forecast", ACCENT3,
         "5-day forecast sourced from OpenWeatherMap's forecast API (updated every 30 minutes). A full temperature chart shows the forecast trend with a ±1.5 °C confidence band and annotated Max/Min points. Below it, humidity and wind forecasts are displayed side-by-side. A complete downloadable forecast table is provided at the bottom. All times are in IST."),
        ("📖", "Walkthrough", ACCENT6,
         "You're here! This page is your user guide. Return anytime if you need a refresher on any feature."),
    ]

    for icon, name, color, desc in pages:
        st.markdown(f"""
        <div class="tour-card" style="border-left: 3px solid {color};">
            <div class="tour-title">{icon} {name}</div>
            <div class="tour-desc">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("🎨 Features at a Glance")

    feat_cols = st.columns(3)
    features = [
        ("🌅 Dynamic Background", "The app background image changes automatically based on real weather conditions — sunny, rainy, foggy, thunderstorm, night, cold, and more. Temperature also influences the image selection."),
        ("🕒 IST Throughout", "All data collection timestamps, chart axes, table columns, and display times use Indian Standard Time (IST, UTC+5:30). No confusion with UTC or local browser time."),
        ("💾 Persistent DB Storage", "Every 1 minute, a new reading is written to the MySQL database. This means your history builds up over time and charts become richer the longer the app runs."),
        ("📅 7-Day Seeded History", "When you visit a new city for the first time, the app auto-seeds 7 days of realistic synthetic history so the charts and heatmaps are immediately populated."),
        ("⚠️ Auto Alerts", "The Overview tab checks live conditions and surfaces smart alerts for extreme heat (≥38°C), rain/storms, high winds (≥10 m/s), and snow — no configuration needed."),
        ("📥 CSV Export", "Every data table has a one-click CSV download. Export today's readings, full history, or 5-day forecast with a single click."),
    ]
    for i, (title, desc) in enumerate(features):
        with feat_cols[i % 3]:
            st.markdown(f"""
            <div class="tour-card">
                <div class="tour-title" style="font-size:15px;">{title}</div>
                <div class="tour-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.subheader("⚙️ Sidebar Controls Reference")

    sidebar_items = {
        "🌍 Country": "Select from India, USA, UK, Japan, or Australia.",
        "🏙️ City": "Each country has 10–15 popular cities. Data is fetched from OpenWeatherMap for your chosen city.",
        "🕒 Time Filter": "Filters the History and Graphs tabs. Options: All, Last 24h, Last 3 Days, Last 7 Days, or time-of-day windows (Night/Morning/Afternoon/Evening).",
        "🔀 Compare Cities": "Multi-select up to 5 additional cities from the same country to compare in the Compare tab.",
        "🔁 Auto Refresh Interval": "Controls how often the Streamlit app re-runs and updates display. Data collection always happens every 1 minute regardless of this setting.",
    }
    for key, val in sidebar_items.items():
        st.markdown(f"**{key}** — {val}")

    st.divider()
    st.markdown("""
    <div style="text-align:center;padding:20px 0;opacity:0.6;font-size:13px;">
        Built with ❤️ by <b>Naveen Raja</b> &nbsp;·&nbsp;
        Powered by <a href="https://openweathermap.org" target="_blank" style="color:#38bdf8;">OpenWeatherMap</a>
        &nbsp;·&nbsp;
        <a href="https://github.com/yaadhav-d/weather-automation-dashboard.git" target="_blank" style="color:#38bdf8;">GitHub</a>
    </div>
    """, unsafe_allow_html=True)

# =============================================================
# FOOTER
# =============================================================

st.divider()
st.markdown(f"""
<div style="text-align:center;color:rgba(255,255,255,0.45);font-size:13px;padding:10px 0;">
    🌦️ Weather Analytics Pro &nbsp;·&nbsp;
    Created by <b>Naveen Raja</b> &nbsp;·&nbsp;
    Powered by <a href="https://openweathermap.org" target="_blank" style="color:#38bdf8;">OpenWeatherMap</a>
    &nbsp;·&nbsp;
    <a href="https://github.com/yaadhav-d/weather-automation-dashboard.git" target="_blank" style="color:#38bdf8;">GitHub</a>
    &nbsp;·&nbsp; All times in IST
</div>
""", unsafe_allow_html=True)