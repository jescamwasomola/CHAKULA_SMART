"""
CHAKULA-SMART
Premium FoodTech Dashboard
Dynamic Pricing | Food Waste Reduction | Food Marketplace
"""

import base64
import sqlite3
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ================================================================
# 1. PROJECT CONFIGURATION
# ================================================================

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pricing_engine import PricingConfig, build_sms, calculate_price  # noqa: E402
from database import (  # noqa: E402
    close_listing,
    get_active_listings,
    get_vendor_listings,
    get_vendor_orders,
    get_vendor_summary,
    initialize_database,
    normalize_phone,
    pretty_phone,
    publish_listing,
    register_vendor_secure,
    reserve_order,
    set_legacy_vendor_pin,
    update_order_status,
    vendor_needs_pin,
    verify_vendor_login,
)
from notify import (  # noqa: E402
    customer_message,
    order_message,
    send_sms,
    sms_enabled,
    whatsapp_link,
)

initialize_database()

IMG_DIRS = [
    Path(__file__).resolve().parent / "images",
    ROOT / "images",
]


def find_image_path(slug):
    """Tafuta picha kwa jina (slug) kwenye folda za images."""
    for folder in IMG_DIRS:
        for ext in ("jpg", "jpeg", "png", "webp"):
            p = folder / f"{slug}.{ext}"
            if p.exists():
                return p
    return None


# Favicon: tumia picha halisi ikiwa ipo (images/logo.png), vinginevyo icon ya Material
_logo = find_image_path("logo")

st.set_page_config(
    page_title="Smart Food",
    page_icon=str(_logo) if _logo else ":material/restaurant:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================================================================
# 2. BRAND COLORS
# ================================================================

GREEN = "#246B45"
DARK_GREEN = "#174A32"
DEEP_GREEN = "#103B29"
LIGHT_GREEN = "#E8F2EB"

GOLD = "#D5A447"
LIGHT_GOLD = "#F8F0DB"
AMBER = "#D58A1F"
ORANGE = "#E4572E"

CREAM = "#FAF8F2"
WHITE = "#FFFFFF"
BEIGE = "#F0EDE3"

INK = "#252820"
MUTED = "#77786F"
LINE = "#E7E4DA"

TERRA = "#C46A43"
RED = "#B94A48"
BLUE = "#527A9B"

# ================================================================
# 3. FOOD INFORMATION
# ================================================================

DISHES = {
    "Wali Maharage": (2000, 1100, "#8a4b14", "#d49a3a"),
    "Wali Nyama": (4000, 2500, "#5c1f14", "#a8402a"),
    "Ugali Dagaa": (2500, 1500, "#3a3a34", "#8d8a7c"),
    "Pilau": (3000, 1800, "#7a4410", "#c47f2a"),
    "Chapati Maharage": (1500, 800, "#8a6a14", "#d2ad3c"),
}

SLUG = {
    dish: dish.lower().replace(" ", "-")
    for dish in DISHES
}

STATUS_SW = {
    "pending": "Inasubiri",
    "confirmed": "Imethibitishwa",
    "cancelled": "Imeghairiwa",
    "active": "Inaendelea",
    "sold_out": "Imeisha",
    "closed": "Imefungwa",
}

# Picha za kadi za ukurasa wa mwanzo (zinatumia picha za vyakula zilizopo)
# Ukipenda picha zako mwenyewe, weka: images/hero.jpg, images/muuzaji.jpg,
# images/mteja.jpg, images/takwimu.jpg
CARD_IMAGES = {
    "hero": "Wali Nyama",
    "muuzaji": "Pilau",
    "mteja": "Wali Maharage",
    "takwimu": "Ugali Dagaa",
}

# ================================================================
# 4. PREMIUM DESIGN SYSTEM
# ================================================================

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;700;800&family=Nunito:wght@400;600;700;800&display=swap');

:root {{
    --green: {GREEN};
    --dark-green: {DARK_GREEN};
    --deep-green: {DEEP_GREEN};
    --gold: {GOLD};
    --cream: {CREAM};
    --beige: {BEIGE};
    --ink: {INK};
    --muted: {MUTED};
    --line: {LINE};
    --terra: {TERRA};
    --orange: {ORANGE};
}}

html, body, [class*="css"], .stApp {{
    font-family: 'Nunito', sans-serif;
    color: var(--ink);
}}

h1, h2, h3, h4 {{
    font-family: 'Baloo 2', sans-serif;
}}

.stApp {{
    background: var(--cream);
}}

#MainMenu, footer, [data-testid="stDecoration"] {{
    visibility: hidden;
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

.block-container {{
    max-width: 1300px;
    padding-top: 1.5rem;
    padding-bottom: 4rem;
    padding-left: 2.5rem;
    padding-right: 2.5rem;
}}

/* SIDEBAR */

[data-testid="stSidebar"] {{
    background: var(--deep-green);
}}

[data-testid="stSidebar"] > div:first-child {{
    padding-top: 1.2rem;
}}

[data-testid="stSidebar"] * {{
    color: #F8F7EF;
}}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
    color: #E3E9E1;
}}

[data-testid="stSidebar"] .stButton > button {{
    background: transparent;
    color: #F8F7EF;
    border: none;
    border-radius: 10px;
    text-align: left;
    font-weight: 700;
    padding: .65rem 1rem;
}}

[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,.12);
    color: white;
}}

[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background: rgba(255,255,255,.16);
    border: none;
}}

.sidebar-brand {{
    display: flex;
    align-items: center;
    gap: .6rem;
    font-family: 'Baloo 2', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: white;
    line-height: 1;
    padding: .3rem 0 1rem;
}}

.sidebar-brand span {{
    color: var(--gold);
}}

.logo-img {{
    width: 40px;
    height: 74px;
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    flex-shrink: 0;
}}

.logo-img.small {{
    width: 34px;
    height: 64px;
}}

.sidebar-caption {{
    font-size: .72rem;
    color: #B8CDBD;
    letter-spacing: .08em;
    font-weight: 700;
    text-transform: uppercase;
    margin-top: 1.1rem;
    margin-bottom: .5rem;
}}

.sidebar-footer {{
    border-top: 1px solid rgba(255,255,255,.15);
    margin-top: 2rem;
    padding-top: 1rem;
    font-size: .8rem;
    color: #B8CDBD;
}}

/* TOP BAR AND HEADINGS */

.top-brand {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.2rem;
    padding-bottom: .8rem;
    border-bottom: 1px solid var(--line);
}}

.brand-left {{
    display: flex;
    align-items: center;
    gap: .6rem;
}}

.brand-name {{
    font-family: 'Baloo 2', sans-serif;
    font-size: 2.3rem;
    font-weight: 800;
    color: var(--green);
    line-height: 1;
}}

.brand-name span {{
    color: var(--orange);
}}

.brand-tag {{
    color: var(--muted);
    font-size: .88rem;
    font-weight: 700;
}}

.page-title {{
    font-family: 'Baloo 2', sans-serif;
    font-size: clamp(1.7rem, 3.2vw, 2.3rem);
    line-height: 1.2;
    font-weight: 700;
    color: var(--ink);
    margin: .2rem 0 .3rem;
}}

.page-subtitle {{
    color: var(--muted);
    font-size: 1rem;
    line-height: 1.6;
    max-width: 700px;
    margin-bottom: 1.2rem;
}}

.section-title {{
    font-family: 'Baloo 2', sans-serif;
    color: var(--ink);
    font-size: 1.4rem;
    font-weight: 700;
    margin-top: 1.4rem;
    margin-bottom: .6rem;
}}

/* BANNER */

.banner {{
    background-color: #F4EFE3;
    background-size: cover;
    background-repeat: no-repeat;
    border-radius: 16px;
    padding: 2.2rem 2.5rem;
    min-height: 240px;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
}}

.banner .inner {{
    max-width: 52%;
}}

.banner h1 {{
    font-family: 'Baloo 2', sans-serif;
    font-size: clamp(1.8rem, 3.6vw, 2.7rem);
    line-height: 1.15;
    font-weight: 800;
    color: var(--deep-green);
    margin: 0 0 .5rem;
    padding: 0;
}}

.banner p {{
    color: #4D4F46;
    font-size: 1.05rem;
    line-height: 1.55;
    font-weight: 600;
    margin: 0;
}}

@media(max-width: 800px) {{
    .banner {{
        padding: 1rem;
        min-height: 200px;
    }}

    .banner .inner {{
        max-width: 100%;
        background: rgba(250,248,242,.9);
        padding: .9rem;
        border-radius: 12px;
    }}
}}

/* CARDS */

.kpi {{
    background: white;
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    min-height: 118px;
}}

.kpi .label {{
    color: var(--muted);
    font-size: .85rem;
    font-weight: 700;
}}

.kpi .value {{
    font-family: 'Baloo 2', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    color: var(--ink);
    margin: .2rem 0 0;
    line-height: 1.2;
}}

.kpi .note {{
    color: var(--muted);
    font-size: .85rem;
}}

.info-card {{
    background: white;
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
}}

.info-card h3 {{
    color: var(--ink);
    font-size: 1.15rem;
    margin: 0 0 .3rem;
}}

.info-card p {{
    color: var(--muted);
    line-height: 1.55;
    font-size: .95rem;
    margin: 0;
}}

.info-card.photo {{
    padding: 0;
    overflow: hidden;
    margin-bottom: .6rem;
}}

.info-card .card-img {{
    height: 150px;
    background-size: cover;
    background-position: center;
}}

.info-card .card-body {{
    padding: 1rem 1.2rem;
}}

/* BUTTONS */

.stButton > button {{
    border-radius: 10px;
    min-height: 2.7rem;
    font-weight: 800;
    border: 1.5px solid var(--green);
    background: white;
    color: var(--green);
    transition: background .15s ease;
}}

.stButton > button:hover {{
    background: var(--beige);
    border-color: var(--green);
    color: var(--dark-green);
}}

.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {{
    background: var(--green);
    border-color: var(--green);
    color: white;
}}

.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {{
    background: var(--dark-green);
    border-color: var(--dark-green);
    color: white;
}}

/* INPUTS */

.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"],
.stMultiSelect div[data-baseweb="select"] {{
    border-radius: 10px;
}}

.stTextInput label,
.stNumberInput label,
.stSelectbox label,
.stSlider label {{
    font-weight: 700;
    color: var(--ink);
}}

.stTabs [data-baseweb="tab"] {{
    font-weight: 800;
    padding: .7rem 1rem;
}}

.stTabs [aria-selected="true"] {{
    color: var(--green);
}}

.stTabs [data-baseweb="tab-highlight"] {{
    background-color: var(--green);
}}

/* FOOD TILES */

.food-tile {{
    border-radius: 12px;
    height: 160px;
    display: flex;
    align-items: flex-end;
    background-size: cover;
    background-position: center;
    overflow: hidden;
    margin-bottom: .5rem;
}}

.food-tile span {{
    display: block;
    width: 100%;
    padding: .8rem 1rem;
    color: white;
    font-family: 'Baloo 2', sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    background: linear-gradient(transparent, rgba(0,0,0,.7));
}}

/* PRICE RESULT */

.verdict {{
    background: white;
    border: 1px solid var(--line);
    border-left: 5px solid var(--accent);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin: 1rem 0;
}}

.verdict .tag {{
    font-size: .9rem;
    font-weight: 800;
    color: var(--accent);
}}

.verdict .price {{
    font-family: 'Baloo 2', sans-serif;
    font-size: clamp(2rem, 4.5vw, 2.8rem);
    color: var(--ink);
    font-weight: 800;
    margin: .1rem 0;
    line-height: 1.2;
}}

.verdict .price s {{
    font-family: 'Nunito', sans-serif;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--muted);
    margin-left: .6rem;
}}

.verdict .description {{
    color: var(--muted);
    font-size: .95rem;
}}

/* OFFERS (kama kwenye app za chakula) */

.offer {{
    background: white;
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: .6rem;
}}

.offer-image {{
    height: 160px;
    background-size: cover;
    background-position: center;
    position: relative;
}}

.offer-badge {{
    position: absolute;
    top: 10px;
    left: 10px;
    background: var(--orange);
    color: white;
    font-weight: 800;
    padding: .2rem .6rem;
    border-radius: 6px;
    font-size: .85rem;
}}

.offer-body {{
    padding: .9rem 1rem 1rem;
}}

.offer-name {{
    font-family: 'Baloo 2', sans-serif;
    color: var(--ink);
    font-size: 1.2rem;
    font-weight: 700;
    line-height: 1.2;
}}

.offer-location {{
    color: var(--muted);
    font-size: .88rem;
    font-weight: 600;
    margin: .2rem 0 0;
}}

.offer-price {{
    color: var(--green);
    font-family: 'Baloo 2', sans-serif;
    font-size: 1.45rem;
    font-weight: 800;
    margin-top: .4rem;
    line-height: 1.2;
}}

.offer-price s {{
    color: var(--muted);
    font-family: 'Nunito', sans-serif;
    font-size: .9rem;
    font-weight: 600;
    margin-left: .5rem;
}}

.offer-stock {{
    display: inline-block;
    background: #FBEDE6;
    color: var(--terra);
    font-size: .82rem;
    font-weight: 800;
    padding: .15rem .55rem;
    border-radius: 6px;
    margin-top: .4rem;
}}

/* HOW IT WORKS */

.how {{
    display: flex;
    gap: .8rem;
    align-items: flex-start;
}}

.how .n {{
    flex: 0 0 34px;
    height: 34px;
    border-radius: 50%;
    background: var(--green);
    color: white;
    font-family: 'Baloo 2', sans-serif;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
}}

.how b {{
    display: block;
    font-size: 1.02rem;
}}

.how span {{
    color: var(--muted);
    font-size: .93rem;
    line-height: 1.5;
}}

/* WELCOME HERO + MSTARI UNAOTEMBEA */

.welcome {{
    background-color: #F4EFE3;
    background-size: cover;
    background-repeat: no-repeat;
    border-radius: 18px;
    padding: 2.5rem 3rem;
    min-height: 340px;
    margin-bottom: .8rem;
    display: flex;
    align-items: center;
    gap: 2rem;
}}

.hero-logo {{
    flex: 0 0 120px;
    height: 224px;
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    animation: float 4s ease-in-out infinite;
}}

.welcome-karibu {{
    font-family: 'Baloo 2', sans-serif;
    font-size: clamp(1.4rem, 3vw, 2rem);
    font-weight: 700;
    color: var(--orange);
    line-height: 1.1;
    animation: rise .8s ease both;
}}

.welcome-title {{
    font-family: 'Baloo 2', sans-serif;
    font-size: clamp(3rem, 8vw, 5.5rem);
    font-weight: 800;
    color: var(--deep-green);
    line-height: 1;
    animation: rise .8s .15s ease both;
}}

.welcome-title span {{
    color: var(--orange);
}}

.welcome-sub {{
    margin-top: .6rem;
    font-size: 1.1rem;
    font-weight: 700;
    color: #4D4F46;
    animation: rise .8s .3s ease both;
}}

.marquee {{
    overflow: hidden;
    white-space: nowrap;
    background: var(--green);
    border-radius: 12px;
    margin: 0 0 1.2rem;
}}

.marquee-track {{
    display: inline-block;
    padding: .65rem 0;
    color: white;
    font-family: 'Baloo 2', sans-serif;
    font-size: 1.25rem;
    font-weight: 700;
    animation: scroll 26s linear infinite;
}}

.marquee-track span {{
    padding: 0 1.4rem;
}}

.marquee-track b {{
    color: var(--gold);
}}

@keyframes scroll {{
    from {{ transform: translateX(0); }}
    to {{ transform: translateX(-50%); }}
}}

@keyframes float {{
    0%, 100% {{ transform: translateY(0); }}
    50% {{ transform: translateY(-10px); }}
}}

@keyframes rise {{
    from {{ opacity: 0; transform: translateY(14px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

@media (prefers-reduced-motion: reduce) {{
    .hero-logo, .welcome-karibu, .welcome-title, .welcome-sub, .marquee-track {{
        animation: none;
    }}
}}

@media(max-width: 800px) {{
    .welcome {{
        padding: 1.2rem;
        gap: 1rem;
        min-height: 240px;
    }}

    .hero-logo {{
        flex-basis: 64px;
        height: 120px;
    }}

    .welcome-text {{
        background: rgba(250,248,242,.9);
        padding: .8rem;
        border-radius: 12px;
    }}
}}

/* SMS AND STATUS */

.sms-box {{
    background: #EDF5EF;
    border: 1px solid #D5E5D8;
    border-radius: 10px;
    padding: .9rem 1.1rem;
    color: var(--deep-green);
    line-height: 1.6;
}}

.status-box {{
    background: white;
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 1rem;
}}

/* EXPANDERS AND TABLES */

[data-testid="stExpander"] {{
    background: white;
    border: 1px solid var(--line);
    border-radius: 10px;
}}

[data-testid="stDataFrame"] {{
    border: 1px solid var(--line);
    border-radius: 10px;
    overflow: hidden;
}}

hr {{
    border-color: var(--line);
}}

.small-muted {{
    color: var(--muted);
    font-size: .85rem;
}}

@media(max-width: 800px) {{
    .block-container {{
        padding-left: 1rem;
        padding-right: 1rem;
        padding-top: 1rem;
    }}

    .food-tile {{
        height: 125px;
    }}

    .how {{
        margin-bottom: .8rem;
    }}
}}
</style>
""",
    unsafe_allow_html=True,
)

# ================================================================
# 5. HELPER FUNCTIONS
# ================================================================


@st.cache_data
def _read_data_uri(path_str, mtime):
    p = Path(path_str)
    ext = p.suffix.lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    encoded = base64.b64encode(p.read_bytes()).decode()
    return f"data:image/{mime};base64,{encoded}"


def image_data_uri(slug):
    """Rudisha picha kama data-URI (base64) kwa jina la faili, au None.

    Picha ikikosekana HAIHIFADHIWI kwenye cache, kwa hiyo ukiweka picha
    mpya kwenye folda ya images/ itaonekana mara moja (bila kurestart).
    """
    p = find_image_path(slug)

    if p is None:
        return None

    return _read_data_uri(str(p), p.stat().st_mtime)


def image_url(dish):
    if dish not in SLUG:
        return None
    return image_data_uri(SLUG[dish])


def bg(dish):
    url = image_url(dish)

    if url:
        return f"background-image:url('{url}')"

    if dish in DISHES:
        c1, c2 = DISHES[dish][2], DISHES[dish][3]
        return f"background-image:linear-gradient(135deg,{c1},{c2})"

    return "background-image:linear-gradient(135deg,#777,#aaa)"


def card_bg(name):
    """Picha ya kadi: jaribu images/<name>.*, kisha picha ya chakula, kisha gradient."""
    url = image_data_uri(name)

    if url:
        return f"background-image:url('{url}')"

    return bg(CARD_IMAGES.get(name, ""))


def hero_bg():
    url = image_data_uri("hero")

    if not url:
        url = image_url(CARD_IMAGES["hero"])

    overlay = (
        "linear-gradient(110deg, rgba(16,59,41,.93) 0%, "
        "rgba(23,74,50,.78) 55%, rgba(31,100,65,.45) 100%)"
    )

    if url:
        return f"background-image:{overlay},url('{url}')"

    return "background-image:linear-gradient(120deg,#103B29 0%,#1F6441 65%,#397A50 100%)"


def banner_bg(slot, position="right center"):
    """Picha ya mandharinyuma ya banner: images/<slot>.* (mfano bg-home)."""
    url = image_data_uri(slot)

    if url:
        return (
            f"background-image:url('{url}');"
            f"background-position:{position}"
        )

    return "background-image:linear-gradient(120deg,#F4EFE3 0%,#E8F2EB 100%)"


def banner(slot, eyebrow, title, text, position="right center"):
    html(
        f'<div class="banner" style="{banner_bg(slot, position)}">'
        '<div class="inner">'
        f'<h1>{title}</h1>'
        f'<p>{text}</p>'
        '</div></div>'
    )


def marquee_html():
    items = [
        "Karibu Smart Food",
        "Chakula kisitupwe",
        "Bei nafuu kila jioni",
        "Karibu tule pamoja",
    ]
    one = "".join(f"<span>{escape(t)}</span><b>•</b>" for t in items)
    # mara mbili ili mwendo usikatike
    return f'<div class="marquee"><div class="marquee-track">{one}{one}</div></div>'


def welcome_hero():
    url = image_data_uri("bg-home")
    logo = image_data_uri("logo")

    style = (
        f"background-image:url('{url}');background-position:right center"
        if url
        else "background-image:linear-gradient(120deg,#F4EFE3,#E8F2EB)"
    )

    logo_div = (
        f'<div class="hero-logo" style="background-image:url(\'{logo}\')"></div>'
        if logo
        else ""
    )

    html(
        f'<div class="welcome" style="{style}">'
        f'{logo_div}'
        '<div class="welcome-text">'
        '<div class="welcome-karibu">Karibu</div>'
        '<div class="welcome-title">Smart <span>Food</span></div>'
        '<div class="welcome-sub">Chagua unavyotaka kutumia app leo.</div>'
        '</div></div>'
    )
    html(marquee_html())


def logo_html(small=False, light=False):
    """Nembo: images/logo.png (nyeusi) au logo-light.png (nyeupe, kwa mandhari nyeusi)."""
    url = image_data_uri("logo-light" if light else "logo")

    if not url:
        return ""

    cls = "logo-img small" if small else "logo-img"
    return f'<div class="{cls}" style="background-image:url(\'{url}\')"></div>'


def now_hour():
    n = datetime.now(ZoneInfo("Africa/Dar_es_Salaam"))
    value = (n.hour + n.minute / 60) * 2
    return min(max(round(value) / 2, 6.0), 23.5)


def money(value):
    return f"TSh {int(value):,}"


def when(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y · %H:%M")
    except (TypeError, ValueError):
        return str(iso)


def html(content):
    st.markdown(content, unsafe_allow_html=True)


def go_to(target):
    current = st.session_state.get("page")

    if current and current != target:
        stack = st.session_state.setdefault("nav_stack", [])
        stack.append(current)
        del stack[:-20]  # kumbukumbu ya kurasa 20 za mwisho

    st.session_state.page = target
    st.session_state.pop("dish", None)


def kpi(label, value, note="", color=GREEN):
    return f"""
    <div class="kpi">
        <div class="label">{label}</div>
        <div class="value" style="color:{color}">{value}</div>
        <div class="note">{note}</div>
    </div>
    """


def offer_html(listing):
    dish = listing["dish"]
    return (
        '<div class="offer">'
        f'<div class="offer-image" style="{bg(dish)}">'
        f'<div class="offer-badge">-{listing["discount_pct"]:.0f}%</div></div>'
        '<div class="offer-body">'
        f'<div class="offer-name">{escape(dish)}</div>'
        f'<div class="offer-location">{escape(listing["area"])} · '
        f'{escape(listing["vendor_name"])}</div>'
        f'<div class="offer-price">{money(listing["current_price"])}'
        f'<s>{money(listing["base_price"])}</s></div>'
        f'<div class="offer-stock">Zimebaki sahani {listing["portions"]}</div>'
        '</div></div>'
    )


def photo_card(image_key, title, text):
    return (
        '<div class="info-card photo">'
        f'<div class="card-img" style="{card_bg(image_key)}"></div>'
        '<div class="card-body">'
        f'<h3>{title}</h3>'
        f'<p>{text}</p>'
        '</div></div>'
    )


def csv_path():
    return ROOT / "data" / "backtest_results.csv"


@st.cache_data
def load(mtime):
    path = csv_path()

    if not path.exists():
        import backtest
        backtest.run().to_csv(path, index=False)

    return pd.read_csv(path)


def login_vendor(vendor):
    if not vendor:
        raise ValueError("Namba ya simu au PIN si sahihi.")

    st.session_state.vendor_id = vendor["id"]
    st.session_state.vendor_name = vendor["name"]
    st.session_state.vendor_area = vendor["area"]
    st.session_state.vendor_phone = vendor["phone"]


def logout_vendor():
    keys = (
        "vendor_id",
        "vendor_name",
        "vendor_area",
        "vendor_phone",
        "dish",
        "legacy_phone",
    )

    for key in keys:
        st.session_state.pop(key, None)


def page_heading(eyebrow, title, description):
    html(
        f'<div class="page-title">{title}</div>'
        f'<div class="page-subtitle">{description}</div>'
    )


def food_tile(dish):
    html(
        f'<div class="food-tile" style="{bg(dish)}">'
        f'<span>{escape(dish)}</span></div>'
    )


# ----------------------------------------------------------------
# MANDHARINYUMA YA APP NZIMA (images/bg-app.jpg)
# Maudhui yako juu ya paneli ya krimu iliyo karibu opaque,
# kwa hiyo maandishi yanasomeka vizuri na nyasi zinaonekana pembeni.
# ----------------------------------------------------------------

_bg_app = image_data_uri("bg-app")

if _bg_app:
    st.markdown(
        f"""
<style>
.stApp {{
    background-image: url('{_bg_app}');
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

.block-container {{
    background: rgba(250, 248, 242, .96);
    border-radius: 18px;
    margin: 1rem auto;
    padding-top: 1.5rem;
    max-width: 1200px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, .22);
}}

@media(max-width: 800px) {{
    .block-container {{
        margin: .5rem auto;
        border-radius: 12px;
    }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


# ================================================================
# 6. SESSION STATE AND NAVIGATION
# ================================================================

st.session_state.setdefault("page", "home")

# Kurasa ambazo kila nafasi (role) inaruhusiwa kuziona.
# Mteja: Mwanzo + Mteja. Muuzaji: Muuzaji + Takwimu.
ROLE_PAGES = {
    "buyer": ["home", "buyer"],
    "seller": ["seller", "stats"],
}


def choose_role(role):
    st.session_state.role = role
    st.session_state.page = ROLE_PAGES[role][0]
    st.session_state.nav_stack = []
    st.session_state.pop("dish", None)


def change_role():
    logout_vendor()
    st.session_state.pop("role", None)
    st.session_state.nav_stack = []
    st.session_state.page = "home"


def can_go_back():
    ss = st.session_state

    return bool(
        ss.get("dish")
        or "legacy_phone" in ss
        or ss.get("nav_stack")
        or "vendor_id" not in ss
    )


def go_back():
    """Rudi hatua moja nyuma: kwanza ndani ya ukurasa, kisha ukurasa uliopita."""
    ss = st.session_state

    # 1. Hatua ndani ya ukurasa
    if ss.get("dish"):
        ss.pop("dish", None)
        return

    if "legacy_phone" in ss:
        ss.pop("legacy_phone", None)
        return

    # 2. Ukurasa uliotangulia
    stack = ss.get("nav_stack", [])

    while stack:
        previous = stack.pop()

        if previous in ROLE_PAGES[ss.role]:
            ss.page = previous
            return

    # 3. Mwanzo kabisa: rudi kuchagua nafasi (isipokuwa muuzaji aliyeingia)
    if "vendor_id" not in ss:
        change_role()


# ----------------------------------------------------------------
# SKRINI YA KUCHAGUA NAFASI (inaonekana mtu anapofungua app)
# ----------------------------------------------------------------

if "role" not in st.session_state:

    # Ficha sidebar kwenye skrini hii
    html(
        '<style>[data-testid="stSidebar"],'
        '[data-testid="stSidebarCollapsedControl"],'
        '[data-testid="collapsedControl"]{display:none}</style>'
    )

    welcome_hero()

    r1, r2 = st.columns(2)

    with r1:
        html(
            photo_card(
                "mteja",
                "Mimi ni mteja",
                "Tafuta chakula kilichopunguzwa bei karibu nawe "
                "na hifadhi sahani yako.",
            )
        )
        if st.button(
            "Endelea kama mteja",
            icon=":material/shopping_bag:",
            type="primary",
            key="role_buyer",
            use_container_width=True,
        ):
            choose_role("buyer")
            st.rerun()

    with r2:
        html(
            photo_card(
                "muuzaji",
                "Mimi ni muuzaji",
                "Chapisha chakula kilichobaki, pata bei inayopendekezwa "
                "na simamia oda zako.",
            )
        )
        if st.button(
            "Endelea kama muuzaji",
            icon=":material/storefront:",
            key="role_seller",
            use_container_width=True,
        ):
            choose_role("seller")
            st.rerun()

    st.stop()


role = st.session_state.role

# Hakikisha mtu haingii ukurasa usio wa nafasi yake
if st.session_state.page not in ROLE_PAGES[role]:
    st.session_state.page = ROLE_PAGES[role][0]

# (jina, icon ya Material - si emoji)
PAGES = {
    "home": ("Mwanzo", ":material/home:"),
    "seller": ("Muuzaji", ":material/storefront:"),
    "buyer": ("Mteja", ":material/shopping_bag:"),
    "stats": ("Takwimu", ":material/bar_chart:"),
}

# Sidebar navigation
with st.sidebar:

    html(
        f'<div class="sidebar-brand">{logo_html(light=True)}'
        '<div>Smart <span>Food</span></div></div>'
        '<div class="sidebar-caption">MENU</div>'
    )

    for key, (label, icon) in PAGES.items():
        if key not in ROLE_PAGES[role]:
            continue

        if st.button(
            label,
            icon=icon,
            key=f"nav_{key}",
            use_container_width=True,
            type="primary" if st.session_state.page == key else "secondary",
        ):
            go_to(key)
            st.rerun()

    st.write("")

    html(
        '<div class="sidebar-caption">LENGO LETU</div>'
        '<div style="font-size:1.05rem;font-weight:700;">'
        'Chakula kisitupwe.</div>'
        '<div style="font-size:.86rem;color:#B8CDBD;line-height:1.6;">'
        'Bei nafuu kwa wateja. Hasara ndogo kwa wauzaji. '
        'Upotevu mdogo wa chakula.</div>'
    )

    st.write("")

    if "vendor_id" in st.session_state:
        st.divider()
        st.caption("AKAUNTI ILIYOINGIWA")
        st.write(f"**{st.session_state.vendor_name}**")

        if st.button(
            "Toka kwenye akaunti",
            icon=":material/logout:",
            key="sidebar_logout",
        ):
            logout_vendor()
            go_to(ROLE_PAGES[role][0])
            st.rerun()

    st.divider()

    st.caption(
        "UNATUMIA KAMA: "
        + ("MTEJA" if role == "buyer" else "MUUZAJI")
    )

    if st.button(
        "Badili nafasi",
        icon=":material/swap_horiz:",
        key="sidebar_change_role",
        use_container_width=True,
    ):
        change_role()
        st.rerun()

    html(
        '<div class="sidebar-footer">'
        'Smart Food · Tanzania'
        '</div>'
    )


# Main top brand
html(
    '<div class="top-brand">'
    f'<div class="brand-left">{logo_html(small=True)}'
    '<div class="brand-name">Smart <span>Food</span></div></div>'
    '<div class="brand-tag">Chakula kisitupwe</div>'
    '</div>'
)

# Kitufe cha kurudi nyuma, kinaonekana kila ukurasa
if can_go_back():
    if st.button(
        "Rudi nyuma",
        icon=":material/arrow_back:",
        key="global_back",
    ):
        go_back()
        st.rerun()


# ================================================================
# 7. HOME PAGE
# ================================================================

page = st.session_state.page

if page == "home":

    banner(
        "bg-home",
        "",
        "Chakula kizuri,<br>bei nafuu.",
        "Nunua chakula kilichobaki kutoka kwa Mama Ntilie karibu nawe, "
        "kwa punguzo, kabla hakijaisha.",
        "right center",
    )

    html(marquee_html())

    q1, _ = st.columns([1, 2])

    with q1:
        if st.button(
            "Tafuta chakula",
            icon=":material/search:",
            type="primary",
            key="home_buyer",
            use_container_width=True,
        ):
            go_to("buyer")
            st.rerun()

    html('<div class="section-title">Ofa za leo</div>')

    todays = get_active_listings()[:4]

    if not todays:

        html(
            '<div class="info-card">'
            '<h3>Hakuna ofa kwa sasa</h3>'
            '<p>Wauzaji wakichapisha chakula kilichobaki, '
            'ofa zitaonekana hapa.</p>'
            '</div>'
        )

    else:

        offer_cols = st.columns(4)

        for i, listing in enumerate(todays):
            with offer_cols[i]:
                html(offer_html(listing))

        if st.button("Ona ofa zote", key="home_all_offers"):
            go_to("buyer")
            st.rerun()

    html('<div class="section-title">Inavyofanya kazi</div>')

    steps = st.columns(3)

    with steps[0]:
        html(
            '<div class="how"><div class="n">1</div>'
            '<div><b>Muuzaji anachapisha</b>'
            '<span>Anaweka sahani zilizobaki na bei inapendekezwa.</span>'
            '</div></div>'
        )

    with steps[1]:
        html(
            '<div class="how"><div class="n">2</div>'
            '<div><b>Bei inashuka jioni</b>'
            '<span>Kadri muda unavyokwenda, punguzo linaongezeka.</span>'
            '</div></div>'
        )

    with steps[2]:
        html(
            '<div class="how"><div class="n">3</div>'
            '<div><b>Mteja anaagiza</b>'
            '<span>Anahifadhi sahani na kuchukua kwa muuzaji.</span>'
            '</div></div>'
        )

    st.write("")
    html(
        '<div class="small-muted">'
        'Smart Food · Mfumo wa majaribio wa kupunguza upotevu wa chakula.'
        '</div>'
    )


# ================================================================
# 8. SELLER PAGE
# ================================================================

elif page == "seller":

    # ------------------------------------------------------------
    # SELLER AUTHENTICATION
    # ------------------------------------------------------------

    if "vendor_id" not in st.session_state:

        banner(
            "bg-seller",
            "SELLER PORTAL",
            "Akaunti ya muuzaji",
            "Ingia kwenye akaunti yako au jisajili ili kuanza "
            "kutangaza chakula chako.",
            "right 35%",
        )

        tab_login, tab_register = st.tabs(
            [":material/lock: Ingia", ":material/person_add: Jisajili"]
        )

        # LOGIN
        with tab_login:

            with st.form("login_form"):

                lp = st.text_input(
                    "Namba ya simu",
                    placeholder="0712 345 678",
                    key="login_phone",
                )

                lpin = st.text_input(
                    "PIN yako",
                    type="password",
                    max_chars=6,
                    key="login_pin",
                )

                login_submit = st.form_submit_button(
                    "Ingia kwenye akaunti",
                    type="primary",
                    use_container_width=True,
                )

            if login_submit:

                try:
                    phone = normalize_phone(lp)

                    if vendor_needs_pin(phone):
                        st.session_state.legacy_phone = phone
                        st.rerun()

                    else:
                        vendor = verify_vendor_login(phone, lpin)
                        login_vendor(vendor)
                        st.rerun()

                except ValueError as error:
                    st.error(str(error))

            # LEGACY ACCOUNT PIN SETUP
            if "legacy_phone" in st.session_state:

                st.info(
                    "Akaunti hii ya zamani haina PIN. "
                    "Weka PIN mpya ili kuendelea."
                )

                with st.form("legacy_pin_form"):

                    legacy_pin = st.text_input(
                        "PIN mpya (tarakimu 4 hadi 6)",
                        type="password",
                        max_chars=6,
                    )

                    legacy_submit = st.form_submit_button(
                        "Weka PIN na ingia",
                        type="primary",
                        use_container_width=True,
                    )

                if legacy_submit:

                    phone = st.session_state.legacy_phone

                    try:
                        if not legacy_pin.isdigit() or not 4 <= len(legacy_pin) <= 6:
                            raise ValueError(
                                "PIN lazima iwe na tarakimu 4 hadi 6."
                            )

                        updated = set_legacy_vendor_pin(
                            phone,
                            legacy_pin,
                        )

                        if updated:
                            vendor = verify_vendor_login(
                                phone,
                                legacy_pin,
                            )

                            login_vendor(vendor)
                            st.session_state.pop("legacy_phone", None)
                            st.success("PIN imewekwa. Umeingia kwenye akaunti.")
                            st.rerun()

                        else:
                            st.error(
                                "Imeshindikana kuweka PIN. "
                                "Jaribu kuingia tena."
                            )

                    except ValueError as error:
                        st.error(str(error))

        # REGISTRATION
        with tab_register:

            with st.form("register_form"):

                rn = st.text_input(
                    "Jina lako",
                    placeholder="Mfano: Mama Asha",
                    key="reg_name",
                )

                rp = st.text_input(
                    "Namba ya simu",
                    placeholder="0712 345 678",
                    key="reg_phone",
                )

                ra = st.text_input(
                    "Eneo unalouzia",
                    placeholder="Mfano: Ubungo",
                    key="reg_area",
                )

                r1 = st.text_input(
                    "Tengeneza PIN",
                    type="password",
                    max_chars=6,
                    key="reg_pin",
                )

                r2 = st.text_input(
                    "Rudia PIN",
                    type="password",
                    max_chars=6,
                    key="reg_pin2",
                )

                register_submit = st.form_submit_button(
                    "Tengeneza akaunti",
                    type="primary",
                    use_container_width=True,
                )

            if register_submit:

                if not all([
                    rn.strip(),
                    rp.strip(),
                    ra.strip(),
                    r1,
                    r2,
                ]):
                    st.error("Tafadhali jaza sehemu zote.")

                elif r1 != r2:
                    st.error("PIN mbili hazilingani.")

                elif not r1.isdigit() or not 4 <= len(r1) <= 6:
                    st.error("PIN lazima iwe na tarakimu 4 hadi 6.")

                else:

                    try:
                        phone = normalize_phone(rp)

                        register_vendor_secure(
                            rn.strip(),
                            phone,
                            ra.strip(),
                            r1,
                        )

                        vendor = verify_vendor_login(phone, r1)
                        login_vendor(vendor)

                        st.success("Akaunti yako imetengenezwa!")
                        st.rerun()

                    except sqlite3.IntegrityError:
                        st.error(
                            "Namba hii tayari imesajiliwa. "
                            "Tumia sehemu ya kuingia."
                        )

                    except ValueError as error:
                        st.error(str(error))

            st.caption(
                "Toleo hili ni prototype. Uthibitisho wa namba kwa SMS/OTP "
                "bado haujaunganishwa."
            )

        st.stop()

    # ------------------------------------------------------------
    # SELLER DASHBOARD
    # ------------------------------------------------------------

    vid = st.session_state.vendor_id

    page_heading(
        "SELLER DASHBOARD",
        f"Karibu, {escape(st.session_state.vendor_name)}",
        f"{escape(st.session_state.vendor_area)} · "
        f"{escape(pretty_phone(st.session_state.vendor_phone))}",
    )

    tab_price, tab_orders, tab_mine = st.tabs(
        [
            ":material/payments: Bei na uchapishaji",
            ":material/inventory_2: Oda za wateja",
            ":material/list_alt: Ofa zangu",
        ]
    )

    # ============================================================
    # SELLER: PRICING
    # ============================================================

    with tab_price:

        html('<div class="section-title">Chagua chakula</div>')

        dish = st.session_state.get("dish")

        if not dish:

            st.write(
                "Chagua aina ya chakula ulichobakiza ili kupata "
                "bei inayopendekezwa."
            )

            cols = st.columns(3)

            for i, d in enumerate(DISHES):

                with cols[i % 3]:

                    food_tile(d)

                    if st.button(
                        f"Chagua {d}",
                        key=f"pick_{i}",
                        use_container_width=True,
                    ):
                        st.session_state.dish = d
                        st.rerun()

        else:

            base_price, cost = DISHES[dish][0], DISHES[dish][1]

            food_tile(dish)

            if st.button(
                "Badilisha chakula",
                icon=":material/arrow_back:",
                key="change_dish",
            ):
                st.session_state.pop("dish", None)
                st.rerun()

            st.write("")

            col1, col2 = st.columns(2)

            with col1:
                remaining = st.number_input(
                    "Sahani zilizobaki",
                    min_value=0,
                    max_value=200,
                    value=20,
                    step=1,
                )

            with col2:
                sold_hr = st.number_input(
                    "Sahani zilizouzwa saa moja iliyopita",
                    min_value=0,
                    max_value=60,
                    value=3,
                    step=1,
                )

            hour = now_hour()
            cfg = PricingConfig()

            with st.expander("Mipangilio ya bei", icon=":material/tune:"):

                col1, col2 = st.columns(2)

                with col1:
                    base_price = st.number_input(
                        "Bei ya kawaida (TSh)",
                        500,
                        10000,
                        int(base_price),
                        step=100,
                    )

                with col2:
                    cost = st.number_input(
                        "Gharama ya kupika (TSh)",
                        100,
                        8000,
                        int(cost),
                        step=100,
                    )

                hour = st.slider(
                    "Muda wa sasa (saa 24)",
                    6.0,
                    23.5,
                    now_hour(),
                    step=0.5,
                )

                start_hour = st.slider(
                    "Punguzo lianze saa",
                    12.0,
                    23.0,
                    17.0,
                    step=0.5,
                )

                max_discount = st.slider(
                    "Punguzo la juu kabisa",
                    0.1,
                    0.8,
                    0.5,
                    step=0.05,
                )

                floor_ratio = st.slider(
                    "Bei ya chini kulingana na gharama",
                    0.3,
                    1.2,
                    0.7,
                    step=0.05,
                )

                cfg = PricingConfig(
                    start_hour=start_hour,
                    max_discount=max_discount,
                    floor_cost_ratio=floor_ratio,
                )

            res = calculate_price(
                base_price,
                cost,
                remaining,
                hour,
                float(sold_hr),
                cfg,
            )

            if res.discount_pct <= 0:
                color = GREEN
                title = "Bei ya kawaida inatosha"
                description = "Bado hakuna haja ya kupunguza bei."

            elif res.discount_pct < 30:
                color = AMBER
                title = "Punguza bei kidogo"
                description = (
                    f"Punguzo la {res.discount_pct:.0f}% "
                    "linaweza kusaidia kuongeza mauzo."
                )

            else:
                color = RED
                title = "Ni wakati wa punguzo"
                description = (
                    f"Punguzo la {res.discount_pct:.0f}% "
                    "linaweza kusaidia chakula kisiendelee kubaki."
                )

            old_price = (
                f"<s>{money(base_price)}</s>"
                if res.discount_pct > 0
                else ""
            )

            html(
                f'<div class="verdict" style="--accent:{color}">'
                f'<div class="tag">{title}</div>'
                f'<div class="price">{money(res.price)}{old_price}</div>'
                f'<div class="description">{description}</div>'
                f'</div>'
            )

            a, b, c = st.columns(3)

            with a:
                html(
                    kpi(
                        "Bei inayopendekezwa",
                        money(res.price),
                        "Kwa sahani moja",
                    )
                )

            with b:
                html(
                    kpi(
                        "Punguzo",
                        f"{res.discount_pct:.0f}%",
                        "Kutoka bei ya kawaida",
                        AMBER,
                    )
                )

            with c:
                html(
                    kpi(
                        "Zinaweza kubaki",
                        f"{res.projected_unsold:.0f}",
                        "Makadirio ya pricing engine",
                        TERRA,
                    )
                )

            if res.notify:

                sms = build_sms(
                    dish,
                    st.session_state.vendor_name,
                    st.session_state.vendor_area,
                    res,
                    cfg.close_hour,
                )

                st.write("")
                html('<div class="section-title">Ujumbe kwa wateja</div>')
                html(
                    f'<div class="sms-box">{escape(sms)}</div>'
                )
                st.caption(
                    "Huu ni mfano wa ujumbe. Kutuma SMS halisi "
                    "bado hakujaunganishwa."
                )

            with st.expander("Kwa nini bei hii imependekezwa?"):
                st.write(res.reason)

            st.divider()

            html('<div class="section-title">Chapisha ofa yako</div>')

            st.write(
                "Baada ya kuchapisha, wateja wataweza kuona ofa "
                "kwenye ukurasa wa Mteja."
            )

            if remaining <= 0:

                st.warning(
                    "Huwezi kutangaza chakula chenye sahani sifuri."
                )

            elif st.button(
                "Chapisha ofa kwa wateja",
                icon=":material/send:",
                type="primary",
                key="publish_offer",
                use_container_width=True,
            ):

                try:
                    listing_id = publish_listing(
                        vid,
                        dish,
                        int(remaining),
                        int(base_price),
                        int(res.price),
                        int(cost),
                        float(res.discount_pct),
                        st.session_state.vendor_area,
                    )

                    st.success(
                        f"Ofa imechapishwa kikamilifu! "
                        f"Namba ya ofa: {listing_id}"
                    )

                except Exception as error:
                    st.error(f"Imeshindikana kuchapisha ofa: {error}")

    # ============================================================
    # SELLER: ORDERS
    # ============================================================

    with tab_orders:

        html('<div class="section-title">Oda za wateja</div>')

        orders = get_vendor_orders(vid)

        if not orders:

            st.info(
                "Bado hujapokea oda. Ofa zako zitaonekana hapa "
                "mteja atakapohifadhi chakula."
            )

        else:

            pending_count = sum(
                1 for order in orders
                if order["status"] == "pending"
            )

            confirmed_count = sum(
                1 for order in orders
                if order["status"] == "confirmed"
            )

            cancelled_count = sum(
                1 for order in orders
                if order["status"] == "cancelled"
            )

            a, b, c = st.columns(3)

            with a:
                html(kpi("Zinasubiri", pending_count, "Oda mpya", AMBER))

            with b:
                html(kpi("Zimethibitishwa", confirmed_count, "Oda zilizokubaliwa"))

            with c:
                html(kpi("Zimeghairiwa", cancelled_count, "Oda zilizofutwa", RED))

            st.write("")

            for order in orders:

                status = STATUS_SW.get(
                    order["status"],
                    order["status"],
                )

                label = (
                    f"Oda #{order['id']} · {order['dish']} · {status}"
                )

                with st.expander(
                    label,
                    expanded=(order["status"] == "pending"),
                ):

                    st.write(
                        f"**Mteja:** {order['customer_name']}  \n"
                        f"**Simu:** {pretty_phone(order['customer_phone'])}  \n"
                        f"**Eneo:** {order.get('area', '—')}  \n"
                        f"**Idadi:** sahani {order['quantity']}  \n"
                        f"**Jumla:** {money(order['total_price'])}  \n"
                        f"**Muda:** {when(order['created_at'])}"
                    )

                    st.link_button(
                        "Wasiliana na mteja kwa WhatsApp",
                        whatsapp_link(
                            order["customer_phone"],
                            f"Habari {order['customer_name']}, kuhusu oda "
                            f"#{order['id']} ya {order['dish']} "
                            f"({st.session_state.vendor_name}).",
                        ),
                        icon=":material/chat:",
                    )

                    if order["status"] == "pending":

                        x, y = st.columns(2)

                        with x:
                            if st.button(
                                "Thibitisha oda",
                                icon=":material/check:",
                                key=f"confirm_{order['id']}",
                                type="primary",
                                use_container_width=True,
                            ):

                                try:
                                    update_order_status(
                                        order["id"],
                                        vid,
                                        "confirmed",
                                    )
                                    if sms_enabled():
                                        send_sms(
                                            order["customer_phone"],
                                            customer_message(
                                                order["id"],
                                                order["dish"],
                                                st.session_state.vendor_name,
                                            ),
                                        )

                                    st.success("Oda imethibitishwa.")
                                    st.rerun()

                                except ValueError as error:
                                    st.error(str(error))

                        with y:
                            if st.button(
                                "Ghairi oda",
                                icon=":material/close:",
                                key=f"cancel_{order['id']}",
                                use_container_width=True,
                            ):

                                try:
                                    update_order_status(
                                        order["id"],
                                        vid,
                                        "cancelled",
                                    )
                                    st.success(
                                        "Oda imeghairiwa na stock imerudishwa."
                                    )
                                    st.rerun()

                                except ValueError as error:
                                    st.error(str(error))

    # ============================================================
    # SELLER: MY LISTINGS
    # ============================================================

    with tab_mine:

        html('<div class="section-title">Muhtasari wa biashara yako</div>')

        summary = get_vendor_summary(vid)

        a, b, c = st.columns(3)

        with a:
            html(
                kpi(
                    "Mauzo yaliyothibitishwa",
                    money(summary["revenue"]),
                    f"Sahani {summary['portions_sold']} zimeuzwa",
                )
            )

        with b:
            html(
                kpi(
                    "Oda zote",
                    summary["orders_total"],
                    f"{summary['pending']} zinasubiri",
                    AMBER,
                )
            )

        with c:
            html(
                kpi(
                    "Oda zinazosubiri",
                    summary["pending"],
                    "Zinahitaji kushughulikiwa",
                    TERRA,
                )
            )

        st.write("")
        html('<div class="section-title">Ofa ulizochapisha</div>')

        listings = get_vendor_listings(vid)

        if not listings:

            st.info("Bado hujachapisha ofa yoyote.")

        else:

            for listing in listings:

                status = STATUS_SW.get(
                    listing["status"],
                    listing["status"],
                )

                with st.expander(
                    f"{listing['dish']} · "
                    f"{money(listing['current_price'])} · {status}"
                ):

                    a, b = st.columns(2)

                    with a:
                        st.write(
                            f"**Sahani zilizobaki:** {listing['portions']}  \n"
                            f"**Bei ya kawaida:** {money(listing['base_price'])}  \n"
                            f"**Bei ya sasa:** {money(listing['current_price'])}"
                        )

                    with b:
                        st.write(
                            f"**Punguzo:** {listing['discount_pct']:.0f}%  \n"
                            f"**Eneo:** {listing['area']}  \n"
                            f"**Ilichapishwa:** {when(listing['created_at'])}"
                        )

                    if (
                        listing["status"] == "active"
                        and st.button(
                            "Funga ofa hii",
                            key=f"close_{listing['id']}",
                        )
                    ):

                        try:
                            close_listing(listing["id"], vid)
                            st.success("Ofa imefungwa.")
                            st.rerun()

                        except ValueError as error:
                            st.error(str(error))


# ================================================================
# 9. BUYER PAGE
# ================================================================

elif page == "buyer":

    banner(
        "bg-buyer",
        "FOOD MARKETPLACE",
        "Chakula kizuri. Bei nafuu.",
        "Gundua ofa za chakula kutoka kwa wauzaji na hifadhi "
        "sahani zako kabla hazijaisha.",
        "center",
    )

    listings = get_active_listings()

    if not listings:

        html(
            '<div class="info-card">'
            '<h3>Hakuna ofa kwa sasa</h3>'
            '<p>Hakuna chakula kilichotangazwa kwa sasa. '
            'Rudi baadaye kuona ofa mpya.</p>'
            '</div>'
        )

    else:

        areas = sorted({
            listing["area"]
            for listing in listings
        })

        f1, f2 = st.columns([2, 1])

        with f1:
            search = st.text_input(
                "Tafuta chakula",
                placeholder="Tafuta chakula, mfano: Pilau",
                label_visibility="collapsed",
            )

        with f2:
            selected_area = st.selectbox(
                "Chagua eneo lako",
                ["Maeneo yote"] + areas,
                label_visibility="collapsed",
            )

        category = st.radio(
            "Aina ya chakula",
            ["Zote"] + sorted({l["dish"] for l in listings}),
            horizontal=True,
            label_visibility="collapsed",
        )

        if selected_area != "Maeneo yote":
            listings = [
                listing for listing in listings
                if listing["area"] == selected_area
            ]

        if category != "Zote":
            listings = [l for l in listings if l["dish"] == category]

        if search.strip():
            q = search.strip().lower()
            listings = [
                l for l in listings
                if q in l["dish"].lower() or q in l["area"].lower()
            ]

        st.caption(f"Ofa zinazopatikana: {len(listings)}")

        cols = st.columns(2)

        for index, listing in enumerate(listings):

            dish = listing["dish"]
            image_style = bg(dish)

            with cols[index % 2]:

                html(
                    f'<div class="offer">'
                    f'<div class="offer-image" style="{image_style}">'
                    f'<div class="offer-badge">'
                    f'-{listing["discount_pct"]:.0f}%'
                    f'</div></div>'
                    f'<div class="offer-body">'
                    f'<div class="offer-name">{escape(dish)}</div>'
                    f'<div class="offer-location">'
                    f'{escape(listing["area"])} · '
                    f'{escape(listing["vendor_name"])}'
                    f'</div>'
                    f'<div class="offer-price">'
                    f'{money(listing["current_price"])}'
                    f'<s>{money(listing["base_price"])}</s>'
                    f'</div>'
                    f'<div class="offer-stock">'
                    f'Zimebaki sahani {listing["portions"]}'
                    f'</div>'
                    f'</div></div>'
                )

                with st.expander(
                    f"Agiza {dish}",
                    icon=":material/shopping_cart:",
                ):

                    quantity = st.number_input(
                        "Unahitaji sahani ngapi?",
                        min_value=1,
                        max_value=int(listing["portions"]),
                        value=1,
                        step=1,
                        key=f"quantity_{listing['id']}",
                    )

                    customer_name = st.text_input(
                        "Jina lako",
                        key=f"name_{listing['id']}",
                    )

                    customer_phone = st.text_input(
                        "Namba yako ya simu",
                        placeholder="0712 345 678",
                        key=f"phone_{listing['id']}",
                    )

                    total = (
                        int(quantity)
                        * int(listing["current_price"])
                    )

                    st.markdown(
                        f"**Jumla ya malipo: {money(total)}**"
                    )

                    if st.button(
                        "Thibitisha oda",
                        type="primary",
                        key=f"order_{listing['id']}",
                        use_container_width=True,
                    ):

                        if len(customer_name.strip()) < 2:

                            st.error("Tafadhali andika jina lako.")

                        else:

                            try:
                                result = reserve_order(
                                    listing["id"],
                                    customer_name.strip(),
                                    normalize_phone(customer_phone),
                                    int(quantity),
                                )

                                st.success(
                                    f"Oda #{result['order_id']} "
                                    f"imehifadhiwa. Jumla: "
                                    f"{money(result['total_price'])}. "
                                    "Muuzaji atathibitisha oda yako."
                                )

                                # Mfikishie muuzaji taarifa ya oda
                                buyer_phone = normalize_phone(customer_phone)
                                note = order_message(
                                    result,
                                    customer_name.strip(),
                                    buyer_phone,
                                )

                                sms_sent = False

                                if sms_enabled():
                                    sms_sent, _ = send_sms(
                                        result["vendor_phone"],
                                        note,
                                    )

                                if sms_sent:
                                    st.info("Muuzaji amearifiwa kwa SMS.")

                                st.link_button(
                                    "Mjulishe muuzaji kwa WhatsApp",
                                    whatsapp_link(result["vendor_phone"], note),
                                    icon=":material/chat:",
                                    use_container_width=True,
                                )

                            except ValueError as error:
                                st.error(str(error))

    st.write("")
    st.caption(
        "Oda ni uhifadhi wa chakula tu. Malipo ya kidijitali "
        "bado hayajaunganishwa."
    )


# ================================================================
# 10. STATISTICS PAGE
# ================================================================

elif page == "stats":

    page_heading(
        "IMPACT & ANALYTICS",
        "Takwimu za Smart Food",
        "Uchambuzi wa makadirio ya athari za dynamic pricing "
        "katika kupunguza upotevu wa chakula na kuboresha mauzo.",
    )

    try:

        df = load(
            csv_path().stat().st_mtime
            if csv_path().exists()
            else 0.0
        )

    except Exception as error:

        st.error(f"Imeshindikana kupakia takwimu: {error}")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        areas = st.multiselect(
            "Chagua maeneo",
            sorted(df.area.dropna().unique()),
            default=sorted(df.area.dropna().unique()),
        )

    with col2:
        dishes = st.multiselect(
            "Chagua chakula",
            sorted(df.dish.dropna().unique()),
            default=sorted(df.dish.dropna().unique()),
        )

    filtered = df[
        df.area.isin(areas)
        & df.dish.isin(dishes)
    ]

    if filtered.empty:

        st.warning(
            "Hakuna data kwa vichujio ulivyochagua."
        )
        st.stop()

    prepared = filtered.prepared.sum()

    if prepared <= 0:

        st.warning(
            "Hakuna kiasi cha chakula kilichopikwa katika data hii."
        )
        st.stop()

    waste_before = (
        (prepared - filtered.base_sold.sum())
        / prepared
        * 100
    )

    waste_after = (
        (prepared - filtered.new_sold.sum())
        / prepared
        * 100
    )

    loss_before = (
        (filtered.prepared - filtered.base_sold)
        * filtered.cost
    ).sum()

    loss_after = (
        (filtered.prepared - filtered.new_sold)
        * filtered.cost
    ).sum()

    profit_gain = (
        filtered.new_profit.sum()
        - filtered.base_profit.sum()
    )

    rescued = int(
        filtered.new_sold.sum()
        - filtered.base_sold.sum()
    )

    html('<div class="section-title">Matokeo kwa ujumla</div>')

    a, b, c, d = st.columns(4)

    with a:
        html(
            kpi(
                "Upotevu baada ya mfumo",
                f"{waste_after:.1f}%",
                f"Kabla: {waste_before:.1f}%",
                GREEN,
            )
        )

    with b:
        html(
            kpi(
                "Hasara iliyopunguzwa",
                money(loss_before - loss_after),
                "Makadirio ya gharama",
                TERRA,
            )
        )

    with c:
        html(
            kpi(
                "Faida iliyoongezeka",
                money(profit_gain),
                "Kwa data iliyochaguliwa",
                GREEN,
            )
        )

    with d:
        html(
            kpi(
                "Sahani zilizookolewa",
                f"{rescued:,}",
                "Makadirio ya sahani",
                GOLD,
            )
        )

    st.write("")
    st.divider()

    # CHART THEME

    chart_layout = dict(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=15, r=15, t=60, b=20),
        font=dict(
            family="Nunito, sans-serif",
            color=INK,
        ),
        legend=dict(
            orientation="h",
            y=-0.2,
        ),
    )

    # WASTE BY AREA

    html('<div class="section-title">Upotevu wa chakula kwa eneo</div>')

    grouped = (
        filtered.groupby("area")
        .agg(
            prepared=("prepared", "sum"),
            before=("base_sold", "sum"),
            after=("new_sold", "sum"),
        )
    )

    grouped["Kabla"] = (
        (grouped.prepared - grouped.before)
        / grouped.prepared
        * 100
    )

    grouped["Baada"] = (
        (grouped.prepared - grouped.after)
        / grouped.prepared
        * 100
    )

    fig = go.Figure()

    fig.add_bar(
        x=grouped.index,
        y=grouped["Kabla"],
        name="Bila Smart Food",
        marker_color=TERRA,
    )

    fig.add_bar(
        x=grouped.index,
        y=grouped["Baada"],
        name="Na Smart Food",
        marker_color=GREEN,
    )

    fig.update_layout(
        title="Kiwango cha upotevu (%)",
        barmode="group",
        yaxis_title="Upotevu (%)",
        **chart_layout,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    # PROFIT OVER TIME

    html('<div class="section-title">Mabadiliko ya faida kwa muda</div>')

    daily = (
        filtered.groupby("date")[
            ["base_profit", "new_profit"]
        ]
        .sum()
        .reset_index()
    )

    fig = go.Figure()

    fig.add_scatter(
        x=daily.date,
        y=daily.base_profit,
        name="Bila mfumo",
        line=dict(
            color=TERRA,
            width=2,
        ),
    )

    fig.add_scatter(
        x=daily.date,
        y=daily.new_profit,
        name="Na Smart Food",
        line=dict(
            color=GREEN,
            width=3,
        ),
    )

    fig.update_layout(
        title="Faida ya kila siku (TSh)",
        yaxis_title="Faida (TSh)",
        **chart_layout,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    # DISH ANALYSIS

    html('<div class="section-title">Uchambuzi kwa aina ya chakula</div>')

    dish_data = (
        filtered.groupby("dish")
        .agg(
            prepared=("prepared", "sum"),
            before=("base_sold", "sum"),
            after=("new_sold", "sum"),
            profit_before=("base_profit", "sum"),
            profit_after=("new_profit", "sum"),
        )
    )

    dish_data["Upotevu kabla (%)"] = (
        (dish_data.prepared - dish_data.before)
        / dish_data.prepared
        * 100
    ).round(1)

    dish_data["Upotevu baada (%)"] = (
        (dish_data.prepared - dish_data.after)
        / dish_data.prepared
        * 100
    ).round(1)

    dish_data["Faida iliyoongezeka (TSh)"] = (
        dish_data.profit_after
        - dish_data.profit_before
    ).round(0).astype(int)

    st.dataframe(
        dish_data[
            [
                "Upotevu kabla (%)",
                "Upotevu baada (%)",
                "Faida iliyoongezeka (TSh)",
            ]
        ],
        use_container_width=True,
    )

    st.caption(
        "MUHIMU: Matokeo haya ni ya majaribio kwa synthetic data. "
        "Yanategemea dhana ya kwamba kila 1% ya punguzo huongeza "
        "mahitaji kwa 2%. Matokeo ya biashara halisi yanaweza "
        "kutofautiana; model inahitaji kuthibitishwa kwa data halisi."
    )


# ================================================================
# 11. INVALID PAGE
# ================================================================

else:

    st.error("Ukurasa haupatikani.")

    if st.button("Rudi mwanzo"):
        go_to("home")
        st.rerun()