import os
import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
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

# =============================================================
# COUNTRY / CITY MAP
# =============================================================

COUNTRY_CITY = {
    "India": {
        "code": "IN",
        "cities": ["Bangalore","Delhi","Mumbai","Chennai","Hyderabad",
                   "Kolkata","Pune","Ahmedabad","Jaipur","Trichy"]
    },
    "USA": {
        "code": "US",
        "cities": ["New York","Los Angeles","Chicago","Houston","Phoenix",
                   "San Francisco","San Diego","Dallas","Seattle","Boston"]
    },
    "UK": {
        "code": "GB",
        "cities": ["London","Manchester","Birmingham","Liverpool",
                   "Leeds","Bristol","Nottingham"]
    },
    "Japan": {
        "code": "JP",
        "cities": ["Tokyo","Osaka","Kyoto","Yokohama","Sapporo","Nagoya"]
    },
    "Australia": {
        "code": "AU",
        "cities": ["Sydney","Melbourne","Brisbane","Perth","Adelaide","Canberra"]
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0c29, #302b63, #24243e) !important;
}
section[data-testid="stSidebar"] * { color: white !important; }

[data-testid="metric-container"] {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 16px;
    padding: 18px 20px !important;
    backdrop-filter: blur(10px);
}
[data-testid="stMetricValue"] { font-size: 2rem !important; }

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 6px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 8px 22px;
    font-weight: 600;
    color: white !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1e3c72, #2a5298) !important;
}

.stDataFrame { border-radius: 12px; overflow: hidden; }
hr { border-color: rgba(255,255,255,0.15) !important; }

.badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
}

.wcard {
    background: linear-gradient(160deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 18px;
    padding: 18px 12px;
    text-align: center;
    color: white;
    transition: transform 0.2s;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}
.wcard:hover { transform: translateY(-3px); }
.wcard .label { font-size: 13px; opacity: 0.75; margin-bottom: 6px; }
.wcard .icon  { font-size: 32px; margin: 6px 0; }
.wcard .temp  { font-size: 22px; font-weight: 700; }
.wcard .sub   { font-size: 12px; opacity: 0.6; margin-top: 4px; }

.graph-label {
    background: rgba(255,255,255,0.06);
    border-left: 4px solid #58a6ff;
    border-radius: 8px;
    padding: 10px 16px;
    margin-bottom: 10px;
    color: white;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# =============================================================
# CHART THEME
# =============================================================

DARK_BG  = "#0d1117"
CARD_BG  = "#161b22"
GRID_COL = "#21262d"
TEXT_COL = "#e6edf3"
ACCENT1  = "#58a6ff"
ACCENT2  = "#f78166"
ACCENT3  = "#3fb950"
ACCENT4  = "#d2a8ff"
ACCENT5  = "#ffa657"

def style_ax(ax, fig, title=""):
    ax.set_facecolor(CARD_BG)
    fig.patch.set_facecolor(DARK_BG)
    ax.tick_params(colors=TEXT_COL, labelsize=9)
    ax.xaxis.label.set_color(TEXT_COL)
    ax.yaxis.label.set_color(TEXT_COL)
    if title:
        ax.set_title(title, color=TEXT_COL, fontweight="bold", fontsize=13, pad=10)
    ax.title.set_color(TEXT_COL)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)
    ax.grid(True, linestyle="--", alpha=0.3, color=GRID_COL)

# =============================================================
# DYNAMIC BACKGROUND
# =============================================================

def set_bg(temp, condition):
    hour  = datetime.now(IST).hour
    cond  = condition.lower()
    night = hour >= 20 or hour < 4

    if "thunderstorm" in cond:
        img = "https://images.pexels.com/photos/1162251/pexels-photo-1162251.jpeg"
    elif "rain" in cond or "drizzle" in cond:
        img = ("https://images.pexels.com/photos/110874/pexels-photo-110874.jpeg"
               if night else "https://images.pexels.com/photos/2448749/pexels-photo-2448749.jpeg")
    elif "snow" in cond:
        img = "https://images.pexels.com/photos/209831/pexels-photo-209831.jpeg"
    elif night:
        img = "https://images.pexels.com/photos/813269/pexels-photo-813269.jpeg"
    elif temp >= 35:
        img = "https://images.pexels.com/photos/1019472/pexels-photo-1019472.jpeg"
    elif temp >= 30:
        img = "https://images.pexels.com/photos/301599/pexels-photo-301599.jpeg"
    elif temp >= 20:
        img = "https://images.pexels.com/photos/8284762/pexels-photo-8284762.jpeg"
    else:
        img = "https://images.pexels.com/photos/209831/pexels-photo-209831.jpeg"

    st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("{img}");
        background-size: cover;
        background-attachment: fixed;
    }}
    [data-testid="stAppViewContainer"] {{
        background-color: rgba(0,0,0,0.62);
    }}
    h1,h2,h3,h4,h5,h6,p,label,span {{ color: white !important; }}
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
    return (datetime.now() - last).total_seconds() / 60 >= minutes

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
                ts = datetime.now() - timedelta(days=days_ago) + timedelta(
                    hours=hour - datetime.now().hour)
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
    df = pd.read_sql(
        text("""
        SELECT recorded_at,temperature,feels_like,humidity,wind,
               pressure,`condition`
        FROM weather_data
        WHERE city=:c AND country=:co AND DATE(recorded_at)=CURDATE()
        ORDER BY recorded_at
        """),
        engine, params={"c": city, "co": country}
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
        WHERE city=:c AND country=:co AND DATE(recorded_at) < CURDATE()
        GROUP BY DATE(recorded_at)
        ORDER BY day DESC LIMIT :d
        """),
        engine, params={"c": city, "co": country, "d": days}
    )
    return df

# =============================================================
# API
# =============================================================

def fetch_current(city, country_code):
    r = requests.get(
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city},{country_code}&appid={API_KEY}&units=metric", timeout=10
    ).json()
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
        "recorded_at": datetime.now()
    }

@st.cache_data(ttl=1800)
def fetch_forecast(city, country_code):
    r = requests.get(
        f"https://api.openweathermap.org/data/2.5/forecast"
        f"?q={city},{country_code}&appid={API_KEY}&units=metric", timeout=10
    ).json()
    rows = []
    for item in r.get("list", []):
        rows.append({
            "time":       datetime.fromtimestamp(item["dt"]),
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
    if temp >= 35:   return "#ef4444"
    elif temp >= 28: return "#f97316"
    elif temp >= 20: return "#22c55e"
    else:            return "#3b82f6"

def apply_time_filter(df, col, option):
    df = df.copy()
    if option == "Last 24h":
        return df[df[col] >= datetime.now() - timedelta(hours=24)]
    elif option == "Last 3 Days":
        return df[df[col] >= datetime.now() - timedelta(days=3)]
    elif option == "Last 7 Days":
        return df[df[col] >= datetime.now() - timedelta(days=7)]
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
    st.markdown("## ⚙️ Dashboard Controls")
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
    REFRESH = st.selectbox("🔁 Auto Refresh", [60,120,300,600,1800],
                           format_func=lambda x: f"{x//60} min")
    st.markdown("---")
    st.markdown(f"**📍 {CITY}, {COUNTRY}**")
    st.caption(f"Last check: {datetime.now().strftime('%H:%M:%S')}")

# =============================================================
# AUTO REFRESH
# =============================================================

st_autorefresh(interval=REFRESH * 1000, key="autorefresh")

# =============================================================
# BOOT
# =============================================================

create_table()

current = fetch_current(CITY, COUNTRY_CODE)
if not current:
    st.error("❌ Could not fetch weather. Check city/API.")
    st.stop()

current["country"] = COUNTRY
seed_past_data(CITY, COUNTRY, COUNTRY_CODE)

if should_insert(CITY, COUNTRY, minutes=REFRESH // 60 or 1):
    insert_weather(current)

set_bg(current["temperature"], current["condition"])

forecast_df = fetch_forecast(CITY, COUNTRY_CODE)
history_df  = load_history(CITY, COUNTRY)
today_df    = load_today(CITY, COUNTRY)
daily_df    = load_daily_avg(CITY, COUNTRY)

hist_filtered  = apply_time_filter(history_df, "recorded_at", TIME_FILTER)
today_filtered = apply_time_filter(today_df,   "recorded_at", TIME_FILTER)

# =============================================================
# HEADER
# =============================================================

st.markdown("# 🌦️ Weather Analytics Pro")
st.caption(
    f"📍 {CITY}, {COUNTRY}  |  "
    f"🕒 {datetime.now().strftime('%A, %d %B %Y  %H:%M')}  |  "
    f"🔁 Refreshes every {REFRESH//60}m"
)
st.divider()

# =============================================================
# TABS
# =============================================================

tab_home, tab_data, tab_graphs, tab_compare, tab_forecast = st.tabs([
    "🏠 Overview", "📊 Data", "📈 Graphs", "🏙️ Compare", "🔮 Forecast"
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
    c4.metric("🌬️ Wind",       f"{current['wind']} m/s")
    c5.metric("🔵 Pressure",    f"{current['pressure']} hPa")
    c6.metric(f"{s_icon} Status", s_label)

    comfort = comfort_index(current["temperature"], current["humidity"])
    vis_km  = round(current["visibility"]/1000, 1) if current["visibility"] else "N/A"
    st.markdown(f"""
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin:12px 0 20px;">
        <div class="badge" style="background:rgba(88,166,255,0.2);color:#58a6ff;">
            ☁️ {current['condition'].title()}</div>
        <div class="badge" style="background:rgba(63,185,80,0.2);color:#3fb950;">
            {comfort}</div>
        <div class="badge" style="background:rgba(247,129,102,0.2);color:#f78166;">
            👁️ Visibility: {vis_km} km</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    cond_l = current["condition"].lower()
    if current["temperature"] >= 38:
        st.warning("🔥 **Extreme Heat Alert** — Stay hydrated.", icon="⚠️")
    if "rain" in cond_l or "thunderstorm" in cond_l:
        st.info("🌧️ **Rain / Storm detected** — Carry an umbrella.", icon="ℹ️")
    if current["wind"] >= 10:
        st.warning("💨 **High Wind Advisory** — Wind above 10 m/s.", icon="⚠️")

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
            fdf[fdf["day"] > datetime.now().date()]
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
        st.subheader("📊 Today's Quick Stats")
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
        st.subheader(f"Today's Readings — {CITY}")
        if today_filtered.empty:
            st.warning("No data for selected time filter.")
        else:
            d = today_filtered.rename(columns={
                "recorded_at":"Recorded At","temperature":"Temp (°C)",
                "feels_like":"Feels Like (°C)","humidity":"Humidity (%)",
                "wind":"Wind (m/s)","pressure":"Pressure (hPa)","condition":"Condition"
            })
            st.dataframe(d, use_container_width=True, height=420)
            st.download_button("⬇️ Download CSV", d.to_csv(index=False),
                               f"{CITY}_today.csv", "text/csv")

    with st2:
        st.subheader(f"Full History — {CITY}  ({TIME_FILTER})")
        if hist_filtered.empty:
            st.warning("No data for selected time filter.")
        else:
            d = hist_filtered.rename(columns={
                "recorded_at":"Recorded At","temperature":"Temp (°C)",
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
# TAB 3 — GRAPHS  (7 graphs)
# ─────────────────────────────────────────────────────────────

with tab_graphs:

    if hist_filtered.empty:
        st.warning(
            "⚠️ No data for the selected time range. "
            "Change the time filter or wait for more data to be collected."
        )
    else:
        x   = hist_filtered["recorded_at"]
        FMT = mdates.DateFormatter("%d-%b %H:%M")

        # ══════════════════════════════════════════════════════
        # GRAPH 1 — Multi-metric stacked: Temp / Humidity / Wind
        # ══════════════════════════════════════════════════════
        st.markdown(
            '<div class="graph-label">'
            '📈 Graph 1 — Temperature, Humidity & Wind Trend (History)'
            '</div>', unsafe_allow_html=True)

        fig1, axes = plt.subplots(3, 1, figsize=(14, 11), sharex=True)
        fig1.patch.set_facecolor(DARK_BG)
        fig1.subplots_adjust(hspace=0.06)

        for ax, (col, ylabel, color) in zip(axes, [
            ("temperature", "Temperature (°C)", ACCENT1),
            ("humidity",    "Humidity (%)",      ACCENT3),
            ("wind",        "Wind (m/s)",        ACCENT2),
        ]):
            y = hist_filtered[col]
            ax.plot(x, y, color=color, linewidth=2.2, zorder=3)
            ax.fill_between(x, y, y.min(), color=color, alpha=0.15)
            ax.scatter(x.iloc[y.argmax()], y.max(),
                       color="red",  s=70, zorder=5, label="Max")
            ax.scatter(x.iloc[y.argmin()], y.min(),
                       color="cyan", s=70, zorder=5, label="Min")
            ax.set_ylabel(ylabel, fontsize=9, color=TEXT_COL)
            ax.legend(facecolor=CARD_BG, labelcolor=TEXT_COL,
                      fontsize=8, loc="upper right")
            style_ax(ax, fig1)

        axes[-1].xaxis.set_major_formatter(FMT)
        plt.xticks(rotation=35, ha="right", color=TEXT_COL, fontsize=8)
        plt.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)

        st.divider()

        # ══════════════════════════════════════════════════════
        # GRAPH 2 — Today's Live Temperature Trend
        # ══════════════════════════════════════════════════════
        st.markdown(
            '<div class="graph-label">'
            "⚡ Graph 2 — Today's Live Temperature Trend"
            '</div>', unsafe_allow_html=True)

        if today_filtered.empty:
            st.info("No today data for this time filter.")
        else:
            xt = today_filtered["recorded_at"]
            yt = today_filtered["temperature"]

            fig2, ax2 = plt.subplots(figsize=(14, 5))
            style_ax(ax2, fig2, f"Today's Temperature — {CITY}, {COUNTRY}")

            ax2.plot(xt, yt, color="#FF6F00", linewidth=3,
                     marker="o", markersize=6,
                     markerfacecolor="white", markeredgecolor="#FF6F00",
                     label="Temp")
            ax2.fill_between(xt, yt, yt.min() - 0.5,
                             color="#FF6F0044", alpha=0.35)

            if len(yt) >= 3:
                roll = yt.rolling(3, min_periods=1).mean()
                ax2.plot(xt, roll, color="white", linewidth=1.5,
                         linestyle="--", alpha=0.55, label="3-pt Rolling Avg")

            imax, imin = yt.argmax(), yt.argmin()
            ax2.scatter(xt.iloc[imax], yt.max(),
                        color="red",  s=120, zorder=5,
                        label=f"Max {yt.max():.1f}°C")
            ax2.scatter(xt.iloc[imin], yt.min(),
                        color="cyan", s=120, zorder=5,
                        label=f"Min {yt.min():.1f}°C")
            ax2.annotate(f"{yt.max():.1f}°C",
                         (xt.iloc[imax], yt.max()),
                         xytext=(0, 12), textcoords="offset points",
                         ha="center", fontsize=10,
                         fontweight="bold", color="red")
            ax2.annotate(f"{yt.min():.1f}°C",
                         (xt.iloc[imin], yt.min()),
                         xytext=(0, -16), textcoords="offset points",
                         ha="center", fontsize=10,
                         fontweight="bold", color="cyan")

            ax2.set_xlabel("Time", color=TEXT_COL)
            ax2.set_ylabel("Temperature (°C)", color=TEXT_COL)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            plt.xticks(rotation=30, ha="right", color=TEXT_COL, fontsize=8)
            ax2.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9)
            plt.tight_layout()
            st.pyplot(fig2)
            plt.close(fig2)

        st.divider()

        # ══════════════════════════════════════════════════════
        # GRAPH 3 — Dual Y-axis: Temp line + Humidity bars
        # ══════════════════════════════════════════════════════
        st.markdown(
            '<div class="graph-label">'
            '📊 Graph 3 — Temperature vs Humidity (Dual Axis)'
            '</div>', unsafe_allow_html=True)

        fig3, ax3 = plt.subplots(figsize=(14, 5))
        style_ax(ax3, fig3, f"Temperature vs Humidity — {CITY}")

        ax3.plot(x, hist_filtered["temperature"],
                 color=ACCENT1, linewidth=2.5, label="Temp (°C)", zorder=3)
        ax3.fill_between(x, hist_filtered["temperature"],
                         hist_filtered["temperature"].min(),
                         color=ACCENT1, alpha=0.10)
        ax3.set_ylabel("Temperature (°C)", color=ACCENT1, fontsize=10)
        ax3.tick_params(axis="y", colors=ACCENT1)

        ax3b = ax3.twinx()
        ax3b.bar(x, hist_filtered["humidity"],
                 color=ACCENT3, alpha=0.28,
                 label="Humidity (%)", width=0.012)
        ax3b.set_ylabel("Humidity (%)", color=ACCENT3, fontsize=10)
        ax3b.tick_params(axis="y", colors=ACCENT3)
        ax3b.set_facecolor(CARD_BG)

        l1, lb1 = ax3.get_legend_handles_labels()
        l2, lb2 = ax3b.get_legend_handles_labels()
        ax3.legend(l1+l2, lb1+lb2,
                   facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9)
        ax3.xaxis.set_major_formatter(FMT)
        plt.xticks(rotation=35, ha="right", color=TEXT_COL, fontsize=8)
        plt.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)

        st.divider()

        # ══════════════════════════════════════════════════════
        # GRAPH 4 — Heatmap: Hour × Day
        # ══════════════════════════════════════════════════════
        st.markdown(
            '<div class="graph-label">'
            '🌡️ Graph 4 — Hourly Temperature Heatmap (Hour × Day)'
            '</div>', unsafe_allow_html=True)

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
                            cmap="RdYlBu_r", interpolation="nearest")
            cbar4 = plt.colorbar(im, ax=ax4)
            cbar4.set_label("°C", color=TEXT_COL)
            cbar4.ax.yaxis.set_tick_params(color=TEXT_COL)
            plt.setp(plt.getp(cbar4.ax.axes, "yticklabels"), color=TEXT_COL)

            ax4.set_xticks(range(len(pivot.columns)))
            ax4.set_xticklabels([str(d) for d in pivot.columns],
                                rotation=45, ha="right",
                                fontsize=8, color=TEXT_COL)
            ax4.set_yticks(range(len(pivot.index)))
            ax4.set_yticklabels([f"{h:02d}:00" for h in pivot.index],
                                fontsize=8, color=TEXT_COL)
            ax4.set_title(f"Hourly Temperature Heatmap — {CITY}",
                          color=TEXT_COL, fontweight="bold", fontsize=13)
            for spine in ax4.spines.values():
                spine.set_edgecolor(GRID_COL)

            plt.tight_layout()
            st.pyplot(fig4)
            plt.close(fig4)

        st.divider()

        # ══════════════════════════════════════════════════════
        # GRAPH 5 — Wind Speed Bar Chart (colour-graded)
        # ══════════════════════════════════════════════════════
        st.markdown(
            '<div class="graph-label">'
            '🌬️ Graph 5 — Wind Speed History (Colour-graded Bars)'
            '</div>', unsafe_allow_html=True)

        fig5, ax5 = plt.subplots(figsize=(14, 4))
        style_ax(ax5, fig5, f"Wind Speed — {CITY}")

        wind_vals  = hist_filtered["wind"].values
        wind_times = hist_filtered["recorded_at"].values
        wind_norm  = (wind_vals - wind_vals.min()) / (np.ptp(wind_vals) + 1e-6)
        cmap_wind  = plt.cm.YlOrRd

        ax5.bar(wind_times, wind_vals,
                color=[cmap_wind(v) for v in wind_norm],
                width=np.timedelta64(25, "m"), zorder=3)
        ax5.set_ylabel("Wind Speed (m/s)", color=TEXT_COL, fontsize=10)
        ax5.xaxis.set_major_formatter(FMT)
        plt.xticks(rotation=35, ha="right", color=TEXT_COL, fontsize=8)

        sm5 = plt.cm.ScalarMappable(
            cmap=cmap_wind,
            norm=plt.Normalize(wind_vals.min(), wind_vals.max()))
        sm5.set_array([])
        cbar5 = plt.colorbar(sm5, ax=ax5, pad=0.01)
        cbar5.set_label("m/s", color=TEXT_COL)
        cbar5.ax.yaxis.set_tick_params(color=TEXT_COL)
        plt.setp(plt.getp(cbar5.ax.axes, "yticklabels"), color=TEXT_COL)

        plt.tight_layout()
        st.pyplot(fig5)
        plt.close(fig5)

        st.divider()

        # ══════════════════════════════════════════════════════
        # GRAPH 6 — Scatter: Temp vs Humidity (wind = colour)
        # ══════════════════════════════════════════════════════
        st.markdown(
            '<div class="graph-label">'
            '🔵 Graph 6 — Temperature vs Humidity Scatter (Correlation)'
            '</div>', unsafe_allow_html=True)

        fig6, ax6 = plt.subplots(figsize=(9, 5))
        style_ax(ax6, fig6,
                 f"Temp vs Humidity Correlation — {CITY}")

        sc_x = hist_filtered["temperature"]
        sc_y = hist_filtered["humidity"]
        sc_c = hist_filtered["wind"]

        sc = ax6.scatter(sc_x, sc_y, c=sc_c, cmap="cool",
                         s=55, alpha=0.75,
                         edgecolors=GRID_COL, linewidths=0.4, zorder=3)
        cbar6 = plt.colorbar(sc, ax=ax6, pad=0.02)
        cbar6.set_label("Wind (m/s)", color=TEXT_COL)
        cbar6.ax.yaxis.set_tick_params(color=TEXT_COL)
        plt.setp(plt.getp(cbar6.ax.axes, "yticklabels"), color=TEXT_COL)

        if len(sc_x) > 3:
            z  = np.polyfit(sc_x, sc_y, 1)
            p  = np.poly1d(z)
            xs = np.linspace(sc_x.min(), sc_x.max(), 100)
            ax6.plot(xs, p(xs), color="white", linewidth=1.8,
                     linestyle="--", alpha=0.6, label="Trend")
            ax6.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9)

        ax6.set_xlabel("Temperature (°C)", color=TEXT_COL, fontsize=10)
        ax6.set_ylabel("Humidity (%)",     color=TEXT_COL, fontsize=10)
        plt.tight_layout()
        st.pyplot(fig6)
        plt.close(fig6)

        st.divider()

        # ══════════════════════════════════════════════════════
        # GRAPH 7 — Daily Avg Temperature Bar Chart (past week)
        # ══════════════════════════════════════════════════════
        st.markdown(
            '<div class="graph-label">'
            '📅 Graph 7 — Daily Average Temperature (Past Week)'
            '</div>', unsafe_allow_html=True)

        if daily_df.empty:
            st.info("Daily averages will appear after at least one full day of data.")
        else:
            daily_plot = daily_df.sort_values("day")
            day_labels = [pd.to_datetime(d).strftime("%a\n%d %b")
                          for d in daily_plot["day"]]
            day_temps  = daily_plot["avg_temp"].values

            fig7, ax7 = plt.subplots(figsize=(10, 5))
            style_ax(ax7, fig7, f"Daily Avg Temperature — {CITY}")

            bars = ax7.bar(day_labels, day_temps,
                           color=[heat_color(t) for t in day_temps],
                           edgecolor=GRID_COL, linewidth=0.7,
                           width=0.55, zorder=3)

            for bar, temp in zip(bars, day_temps):
                ax7.text(bar.get_x() + bar.get_width()/2,
                         bar.get_height() + 0.15,
                         f"{temp}°C",
                         ha="center", va="bottom",
                         fontsize=11, fontweight="bold", color=TEXT_COL)

            avg_line = day_temps.mean()
            ax7.axhline(avg_line, color="white", linewidth=1.4,
                        linestyle="--", alpha=0.55,
                        label=f"Week Avg: {avg_line:.1f}°C")

            ax7.set_ylabel("Temperature (°C)", color=TEXT_COL, fontsize=10)
            ax7.tick_params(axis="x", colors=TEXT_COL, labelsize=9)
            ax7.set_ylim(0, day_temps.max() + 4)
            ax7.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9)
            plt.tight_layout()
            st.pyplot(fig7)
            plt.close(fig7)

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
        st.subheader("📈 Temperature Trend Comparison (Today)")
        fig_c, ax_c = plt.subplots(figsize=(14, 5))
        style_ax(ax_c, fig_c, "City Temperature Comparison — Today")

        comp_colors = [ACCENT1, ACCENT2, ACCENT3, ACCENT4, ACCENT5, "#34d399"]
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
        ax_c.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.xticks(rotation=30, ha="right", color=TEXT_COL, fontsize=8)
        ax_c.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9)
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
                        edgecolor=GRID_COL, linewidth=0.8, width=0.5)
        for bar, temp in zip(bars, bt):
            ax_b.text(bar.get_x() + bar.get_width()/2,
                      bar.get_height() + 0.2,
                      f"{temp}°C",
                      ha="center", fontsize=10,
                      fontweight="bold", color=TEXT_COL)
        ax_b.set_ylabel("Temperature (°C)", color=TEXT_COL)
        plt.tight_layout()
        st.pyplot(fig_b)
        plt.close(fig_b)
    else:
        st.info("👈 Select cities from the sidebar to compare.")

# ─────────────────────────────────────────────────────────────
# TAB 5 — FORECAST
# ─────────────────────────────────────────────────────────────

with tab_forecast:
    st.subheader(f"🔮 5-Day Detailed Forecast — {CITY}")

    if forecast_df.empty:
        st.warning("Could not load forecast.")
    else:
        xf = forecast_df["time"]
        yf = forecast_df["temp"]

        # Forecast temperature
        fig_f, ax_f = plt.subplots(figsize=(14, 5))
        style_ax(ax_f, fig_f, f"Forecast — {CITY}, {COUNTRY}")

        ax_f.plot(xf, yf, color="#f97316", linewidth=3,
                  marker="o", markersize=5,
                  markerfacecolor="white", markeredgecolor="#f97316",
                  label="Forecast Temp", zorder=4)
        for lw in [8, 5, 3]:
            ax_f.plot(xf, yf, color="#f97316", linewidth=lw, alpha=0.05)

        ax_f.fill_between(xf, yf-1.5, yf+1.5,
                          color="#22c55e", alpha=0.18, label="±1.5°C band")
        ax_f.fill_between(xf, yf, yf.min()-1, color="#f97316", alpha=0.10)

        mi, ma = yf.idxmin(), yf.idxmax()
        ax_f.scatter(xf[ma], yf.max(), color="red",  s=120, zorder=6)
        ax_f.scatter(xf[mi], yf.min(), color="cyan", s=120, zorder=6)
        ax_f.annotate(f"Max {yf.max():.1f}°C", (xf[ma], yf.max()),
                      xytext=(0,14), textcoords="offset points",
                      ha="center", fontsize=10, fontweight="bold", color="red")
        ax_f.annotate(f"Min {yf.min():.1f}°C", (xf[mi], yf.min()),
                      xytext=(0,-18), textcoords="offset points",
                      ha="center", fontsize=10, fontweight="bold", color="cyan")

        ax_f.set_xlabel("Date & Time", color=TEXT_COL)
        ax_f.set_ylabel("Temperature (°C)", color=TEXT_COL)
        ax_f.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
        plt.xticks(rotation=40, ha="right", color=TEXT_COL, fontsize=8)
        ax_f.legend(facecolor=CARD_BG, labelcolor=TEXT_COL, fontsize=9)
        plt.tight_layout()
        st.pyplot(fig_f)
        plt.close(fig_f)

        st.divider()

        # Humidity forecast
        st.subheader("💧 Humidity Forecast")
        fig_h, ax_h = plt.subplots(figsize=(14, 4))
        style_ax(ax_h, fig_h, "Humidity Forecast")
        ax_h.fill_between(forecast_df["time"], forecast_df["humidity"],
                          color=ACCENT3, alpha=0.45)
        ax_h.plot(forecast_df["time"], forecast_df["humidity"],
                  color=ACCENT3, linewidth=2)
        ax_h.set_ylabel("Humidity (%)", color=TEXT_COL)
        ax_h.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
        plt.xticks(rotation=40, ha="right", color=TEXT_COL, fontsize=8)
        plt.tight_layout()
        st.pyplot(fig_h)
        plt.close(fig_h)

        st.divider()

        # Wind forecast
        st.subheader("🌬️ Wind Speed Forecast")
        fig_w, ax_w = plt.subplots(figsize=(14, 4))
        style_ax(ax_w, fig_w, "Wind Speed Forecast")
        ax_w.bar(forecast_df["time"], forecast_df["wind"],
                 color=ACCENT2, alpha=0.8, width=0.04)
        ax_w.set_ylabel("Wind Speed (m/s)", color=TEXT_COL)
        ax_w.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
        plt.xticks(rotation=40, ha="right", color=TEXT_COL, fontsize=8)
        plt.tight_layout()
        st.pyplot(fig_w)
        plt.close(fig_w)

        st.divider()

        # Forecast table
        st.subheader("📋 Forecast Table")
        fc_display = forecast_df.rename(columns={
            "time":"Date & Time","temp":"Temp (°C)",
            "feels_like":"Feels Like (°C)","humidity":"Humidity (%)",
            "wind":"Wind (m/s)","condition":"Condition"
        })
        st.dataframe(fc_display, use_container_width=True, height=380)
        st.download_button("⬇️ Download Forecast CSV",
                           fc_display.to_csv(index=False),
                           f"{CITY}_forecast.csv", "text/csv")

# =============================================================
# FOOTER
# =============================================================

st.divider()
st.markdown("""
<style>
.footer {
    text-align:center;
    color:rgba(255,255,255,0.5);
    font-size:13px;
    padding:12px 0;
}
.footer a { color:#58a6ff; text-decoration:none; }
</style>
<div class="footer">
    Built with ❤️ by <b>YAADHAV</b> &nbsp;|&nbsp;
    Powered by <a href="https://openweathermap.org" target="_blank">OpenWeatherMap</a>
    &nbsp;|&nbsp;
    <a href="https://github.com/yaadhav-d/weather-automation-dashboard.git" target="_blank">GitHub</a>
</div>
""", unsafe_allow_html=True)
