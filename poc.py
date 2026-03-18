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
# CONFIGURE EMAIL (ENV VARS)
# -------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_ADDRESS = "delicsouza@gmail.com"
EMAIL_PASSWORD = os.getenv("emailpassword")  # matches what you set
TO_ADDRESS = EMAIL_ADDRESS  # send to yourself

if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    raise ValueError("Missing EMAIL_ADDRESS or EMAILPASSWORD environment variables")

# -------------------------
# NEWS
# -------------------------
def get_headlines(out_stream):
    print("GLOBAL HEADLINES", file=out_stream)
    print("-" * 15, file=out_stream)

    feeds = {
        "GEOPOLITICS": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "FINANCE": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "US POLITICS": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml"
    }

    for category, url in feeds.items():
        print(category, file=out_stream)

        try:
            feed = feedparser.parse(url)

            if feed.entries:
                for article in feed.entries[:5]:
                    if hasattr(article, "published_parsed") and article.published_parsed:
                        pub_time = datetime(*article.published_parsed[:6]).strftime("%H:%M")
                    else:
                        pub_time = "--:--"

                    print(f"  [{pub_time}] {article.title}", file=out_stream)
            else:
                print("  No headlines retrieved.", file=out_stream)

        except Exception:
            print("  Feed error", file=out_stream)

        print(file=out_stream)

# -------------------------
# MAIN BRIEF
# -------------------------
def get_briefing(out_stream):
    print("=" * 15, file=out_stream)
    print("DAILY BRIEF", file=out_stream)
    print("=" * 15, file=out_stream)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", file=out_stream)

    try:
        # HEADLINES
        get_headlines(out_stream)

        # -------------------------
        # OIL MARKET
        # -------------------------
        print("OIL MARKET", file=out_stream)
        print("-" * 70, file=out_stream)

        end = datetime.now()
        start = end - timedelta(days=60)

        wti = yf.download("CL=F", start=start, end=end, progress=False)
        brent = yf.download("BZ=F", start=start, end=end, progress=False)

        if wti.empty or brent.empty or len(wti) < 22 or len(brent) < 22:
            print("Oil data unavailable\n", file=out_stream)
        else:
            def calc_metrics(df):
                curr = df["Close"].iloc[-1]
                prev = df["Close"].iloc[-2]
                d5 = df["Close"].iloc[-6]
                d30 = df["Close"].iloc[-22]

                return {
                    "curr": curr,
                    "chg1": ((curr - prev) / prev) * 100,
                    "chg5": ((curr - d5) / d5) * 100,
                    "chg30": ((curr - d30) / d30) * 100,
                    "high": df["High"].iloc[-22:].max(),
                    "low": df["Low"].iloc[-22:].min()
                }

            w = calc_metrics(wti)
            b = calc_metrics(brent)

            print("WTI CRUDE", file=out_stream)
            print(f"  Price: ${w['curr']:.2f}", file=out_stream)
            print(f"  1D: {w['chg1']:+.2f}%  5D: {w['chg5']:+.2f}%  30D: {w['chg30']:+.2f}%", file=out_stream)
            print(f"  Range: ${w['low']:.2f} – ${w['high']:.2f}\n", file=out_stream)

            print("BRENT CRUDE", file=out_stream)
            print(f"  Price: ${b['curr']:.2f}", file=out_stream)
            print(f"  1D: {b['chg1']:+.2f}%  5D: {b['chg5']:+.2f}%  30D: {b['chg30']:+.2f}%", file=out_stream)
            print(f"  Range: ${b['low']:.2f} – ${b['high']:.2f}\n", file=out_stream)

            spread = b["curr"] - w["curr"]
            ratio = b["curr"] / w["curr"]

            print(f"SPREAD: ${spread:+.2f} | RATIO: {ratio:.3f}\n", file=out_stream)

        # -------------------------
        # INDICES
        # -------------------------
        print("STOCK MARKET", file=out_stream)
        print("-" * 70, file=out_stream)

        indices = {
            "^GSPC": "S&P 500",
            "^IXIC": "NASDAQ",
            "^DJI": "DOW",
        }

        for ticker, name in indices.items():
            try:
                df = yf.download(ticker, period="5d", progress=False)
                if df.empty or len(df) < 2:
                    continue

                curr = df["Close"].iloc[-1]
                prev = df["Close"].iloc[-2]
                chg = ((curr - prev) / prev) * 100
                direction = "↑" if chg >= 0 else "↓"

                print(f"{name:10} {curr:>10,.0f} {direction} {chg:+.2f}%", file=out_stream)

            except:
                continue

        # -------------------------
        # TOP STOCKS
        # -------------------------
        print("\nTOP MOVERS", file=out_stream)
        print("-" * 15, file=out_stream)

        universe = [
            "MSFT","AAPL","NVDA","AMZN","GOOGL",
            "META","TSLA","JPM","XOM","V"
        ]

        results = []

        for ticker in universe:
            try:
                df = yf.download(ticker, period="5d", progress=False)
                if df.empty or len(df) < 2:
                    continue

                curr = df["Close"].iloc[-1]
                prev = df["Close"].iloc[-2]
                chg = ((curr - prev) / prev) * 100

                results.append((ticker, curr, chg))
            except:
                continue

        results.sort(key=lambda x: abs(x[2]), reverse=True)

        for ticker, price, chg in results[:10]:
            direction = "↑" if chg >= 0 else "↓"
            print(f"{ticker:6} ${price:>8,.2f} {direction} {chg:+.2f}%", file=out_stream)

        print("\n" + "=" * 70, file=out_stream)

    except Exception as e:
        print(f"ERROR: {e}", file=out_stream)
        traceback.print_exc(file=out_stream)

# -------------------------
# EMAIL
# -------------------------
def send_email(content):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = TO_ADDRESS
        msg["Subject"] = f"Daily Brief - {datetime.now().strftime('%Y-%m-%d')}"

        msg.attach(MIMEText(content, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print("Email sent successfully.")

    except Exception as e:
        print(f"Email failed: {e}")

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    buffer = io.StringIO()
    get_briefing(buffer)
    content = buffer.getvalue()
    buffer.close()

    send_email(content)