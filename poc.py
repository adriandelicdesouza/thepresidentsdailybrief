import yfinance as yf
import feedparser
from datetime import datetime, timedelta
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import traceback

# -------------------------
# CONFIGURE EMAIL
# -------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_ADDRESS = "delicsouza@gmail.com"
EMAIL_PASSWORD = os.getenv("emailpassword")
TO_ADDRESS = EMAIL_ADDRESS

if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    raise ValueError("Missing EMAIL_ADDRESS or EMAILPASSWORD environment variables")

# -------------------------
# HELPER: PRINT TO BOTH
# -------------------------
def out_print(out_stream, msg=""):
    print(msg)
    print(msg, file=out_stream)

# Safely get a scalar from a DataFrame cell
def safe_scalar(val):
    try:
        # If val is a Series with one element, get that
        if hasattr(val, "__len__") and not isinstance(val, (str, bytes)) and len(val) == 1:
            return float(val.iloc[0])
        return float(val)
    except Exception:
        return None

# -------------------------
# NEWS
# -------------------------
def get_headlines(out_stream):
    out_print(out_stream, "GLOBAL HEADLINES")
    out_print(out_stream, "-" * 15)

    feeds = {
        "GEOPOLITICS": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "FINANCE": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "US POLITICS": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml"
    }

    for category, url in feeds.items():
        out_print(out_stream, category)
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                for article in feed.entries[:5]:
                    pub_time = "--:--"
                    if hasattr(article, "published_parsed") and article.published_parsed:
                        pub_time = datetime(*article.published_parsed[:6]).strftime("%H:%M")
                    out_print(out_stream, f"  [{pub_time}] {article.title}")
            else:
                out_print(out_stream, "  No headlines retrieved.")
        except Exception:
            out_print(out_stream, "  Feed error")
        out_print(out_stream)

# -------------------------
# OIL & COMMODITIES
# -------------------------
def get_commodities(out_stream):
    out_print(out_stream, "OIL & COMMODITIES")
    out_print(out_stream, "-" * 70)

    end = datetime.now()
    start = end - timedelta(days=60)

    symbols = {
        "WTI CRUDE": "CL=F",
        "BRENT CRUDE": "BZ=F",
        "Gold": "GC=F",
        "Silver": "SI=F",
        "Copper": "HG=F"
    }

    def calc_stats(df):
        if df is None or df.empty or len(df) < 22:
            return None
        stats = {}
        stats["curr"] = safe_scalar(df["Close"].iloc[-1])
        stats["prev1"] = safe_scalar(df["Close"].iloc[-2])
        stats["d5"] = safe_scalar(df["Close"].iloc[-6])
        stats["d30"] = safe_scalar(df["Close"].iloc[-22])
        stats["high"] = safe_scalar(df["High"].iloc[-22:].max())
        stats["low"] = safe_scalar(df["Low"].iloc[-22:].min())
        return stats

    all_stats = {}
    for name, ticker in symbols.items():
        try:
            df = yf.download(ticker, start=start, end=end, progress=False)
        except Exception:
            df = None
        stats = calc_stats(df)
        if not stats:
            out_print(out_stream, f"{name} data unavailable")
            continue

        all_stats[name] = stats
        curr = stats["curr"]
        out_print(out_stream, f"{name}")
        if curr is not None:
            chg1 = ((curr - stats["prev1"]) / stats["prev1"] * 100) if stats["prev1"] else None
            chg5 = ((curr - stats["d5"]) / stats["d5"] * 100) if stats["d5"] else None
            chg30 = ((curr - stats["d30"]) / stats["d30"] * 100) if stats["d30"] else None

            out_print(out_stream, f"  Price: ${curr:.2f}" if curr is not None else "  Price: N/A")
            out_print(out_stream,
                      f"  1D: {chg1:+.2f}%  5D: {chg5:+.2f}%  30D: {chg30:+.2f}%"
                      if chg1 is not None else "  Change: N/A")
            out_print(out_stream,
                      f"  Range: ${stats['low']:.2f} – ${stats['high']:.2f}" if stats["low"] is not None else "  Range: N/A")
        out_print(out_stream, "")

    # Spread
    if "WTI CRUDE" in all_stats and "BRENT CRUDE" in all_stats:
        w = all_stats["WTI CRUDE"]["curr"]
        b = all_stats["BRENT CRUDE"]["curr"]
        if w and b:
            spread = b - w
            ratio = b / w if w else None
            out_print(out_stream, f"SPREAD: ${spread:+.2f} | RATIO: {ratio:.3f}" if ratio else "Spread: N/A")
        out_print(out_stream)

# -------------------------
# STOCK MARKET
# -------------------------
def get_stock_market(out_stream):
    out_print(out_stream, "STOCK MARKET")
    out_print(out_stream, "-" * 70)

    indices = {
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ",
        "^DJI": "DOW",
        "^FTSE": "FTSE 100",
        "^N225": "Nikkei 225",
        "^HSI": "Hang Seng"
    }

    for ticker, name in indices.items():
        try:
            df = yf.download(ticker, period="5d", progress=False)
        except Exception:
            df = None
        if df is None or df.empty or len(df) < 2:
            continue
        curr = safe_scalar(df["Close"].iloc[-1])
        prev = safe_scalar(df["Close"].iloc[-2])
        if curr is None or prev is None:
            continue
        chg = ((curr - prev) / prev) * 100
        direction = "↑" if chg >= 0 else "↓"
        out_print(out_stream, f"{name:10} {curr:>10,.0f} {direction} {chg:+.2f}%")

    out_print(out_stream, "\nTOP MOVERS")
    out_print(out_stream, "-" * 15)

    universe = ["MSFT","AAPL","NVDA","AMZN","GOOGL","META","TSLA","JPM","XOM","V"]
    movers = []
    for tkr in universe:
        try:
            df = yf.download(tkr, period="5d", progress=False)
        except Exception:
            df = None
        if df is None or df.empty or len(df) < 2:
            continue
        price = safe_scalar(df["Close"].iloc[-1])
        prev_price = safe_scalar(df["Close"].iloc[-2])
        if price is None or prev_price is None:
            continue
        pct = ((price - prev_price) / prev_price) * 100
        movers.append((tkr, price, pct))

    movers.sort(key=lambda x: abs(x[2]), reverse=True)
    for tkr, price, pct in movers[:10]:
        info = yf.Ticker(tkr).info
        pe = info.get("trailingPE", "N/A")
        mcap = info.get("marketCap", "N/A")
        div = info.get("dividendYield", "N/A")
        direction = "↑" if pct >= 0 else "↓"
        out_print(out_stream,
                  f"{tkr:6} ${price:>8,.2f} {direction} {pct:+.2f}% | P/E: {pe} | MktCap: {mcap} | DivYield: {div}")

# -------------------------
# MAIN BRIEF
# -------------------------
def get_briefing(out_stream):
    out_print(out_stream, "=" * 15)
    out_print(out_stream, "DAILY BRIEF")
    out_print(out_stream, "=" * 15)
    out_print(out_stream, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        get_headlines(out_stream)
        get_commodities(out_stream)
        get_stock_market(out_stream)
        out_print(out_stream, "\n" + "=" * 70)
    except Exception as e:
        out_print(out_stream, f"ERROR: {e}")
        traceback.print_exc(file=out_stream)

# -------------------------
# SEND EMAIL
# -------------------------
def send_email(content):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_ADDRESS
    msg["Subject"] = f"Daily Brief - {datetime.now().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText(content, "plain"))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    buffer = io.StringIO()
    get_briefing(buffer)
    content = buffer.getvalue()
    buffer.close()
    send_email(content)