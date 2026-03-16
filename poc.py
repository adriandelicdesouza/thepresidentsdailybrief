import yfinance as yf
import feedparser
from datetime import datetime, timedelta
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys

# -------------------------
# CONFIGURE YOUR EMAIL
# -------------------------
SMTP_SERVER = "smtp.gmail.com"   # example for Gmail
SMTP_PORT = 587
EMAIL_ADDRESS = "delicsouza@gmail.com"   # your email
EMAIL_PASSWORD = "rtsr jxxo hkfd zfaa"     # app password if using Gmail
TO_ADDRESS = "delicsouza@gmail.com"      # recipient


def get_headlines(out_stream):
    print("GLOBAL HEADLINES", file=out_stream)
    print("-" * 70, file=out_stream)

    feeds = {
        "GEOPOLITICS": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "FINANCE": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "US POLITICS": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml"
    }

    for category, url in feeds.items():
        print(category, file=out_stream)
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
        print(file=out_stream)


def get_briefing(out_stream):
    print("\n" + "=" * 15, file=out_stream)
    print("DAILY BRIEF", file=out_stream)
    print("=" * 15, file=out_stream)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", file=out_stream)

    try:
        # GLOBAL HEADLINES
        get_headlines(out_stream)

        # OIL MARKET
        print("OIL MARKET", file=out_stream)
        print("-" * 70, file=out_stream)

        end = datetime.now()
        start = end - timedelta(days=60)

        wti = yf.download("CL=F", start=start, end=end, progress=False)
        brent = yf.download("BZ=F", start=start, end=end, progress=False)

        if not wti.empty and not brent.empty:
            wti_curr = wti["Close"].iloc[-1].item()
            wti_prev = wti["Close"].iloc[-2].item()
            wti_5d = wti["Close"].iloc[-6].item()
            wti_30d = wti["Close"].iloc[-22].item()
            wti_chg_1d = ((wti_curr - wti_prev) / wti_prev) * 100
            wti_chg_5d = ((wti_curr - wti_5d) / wti_5d) * 100
            wti_chg_30d = ((wti_curr - wti_30d) / wti_30d) * 100
            wti_high = wti["High"].iloc[-22:].max().item()
            wti_low = wti["Low"].iloc[-22:].min().item()

            brent_curr = brent["Close"].iloc[-1].item()
            brent_prev = brent["Close"].iloc[-2].item()
            brent_5d = brent["Close"].iloc[-6].item()
            brent_30d = brent["Close"].iloc[-22].item()
            brent_chg_1d = ((brent_curr - brent_prev) / brent_prev) * 100
            brent_chg_5d = ((brent_curr - brent_5d) / brent_5d) * 100
            brent_chg_30d = ((brent_curr - brent_30d) / brent_30d) * 100
            brent_high = brent["High"].iloc[-22:].max().item()
            brent_low = brent["Low"].iloc[-22:].min().item()

            spread = brent_curr - wti_curr
            ratio = brent_curr / wti_curr

            print("WTI CRUDE", file=out_stream)
            print(f"  Price:        ${wti_curr:.2f}/bbl", file=out_stream)
            print(f"  1D Change:    {wti_chg_1d:+.2f}%", file=out_stream)
            print(f"  5D Change:    {wti_chg_5d:+.2f}%", file=out_stream)
            print(f"  30D Change:   {wti_chg_30d:+.2f}%", file=out_stream)
            print(f"  30D Range:    ${wti_low:.2f} – ${wti_high:.2f}", file=out_stream)
            print(file=out_stream)

            print("BRENT CRUDE", file=out_stream)
            print(f"  Price:        ${brent_curr:.2f}/bbl", file=out_stream)
            print(f"  1D Change:    {brent_chg_1d:+.2f}%", file=out_stream)
            print(f"  5D Change:    {brent_chg_5d:+.2f}%", file=out_stream)
            print(f"  30D Change:   {brent_chg_30d:+.2f}%", file=out_stream)
            print(f"  30D Range:    ${brent_low:.2f} – ${brent_high:.2f}", file=out_stream)
            print(file=out_stream)

            print("BRENT–WTI SPREAD", file=out_stream)
            print(f"  Spread:       ${spread:+.2f}/bbl", file=out_stream)
            print(f"  Ratio:        {ratio:.3f}", file=out_stream)

        # STOCK MARKET
        print("\nSTOCK MARKET", file=out_stream)
        print("-" * 70, file=out_stream)

        indices = {
            "^GSPC": "S&P 500",
            "^IXIC": "NASDAQ",
            "^DJI": "DOW",
        }

        print("INDICES", file=out_stream)
        for ticker, name in indices.items():
            idx = yf.download(ticker, period="5d", progress=False)
            if not idx.empty:
                curr = idx["Close"].iloc[-1].item()
                prev = idx["Close"].iloc[-2].item()
                chg = ((curr - prev) / prev) * 100
                direction = "↑" if chg >= 0 else "↓"
                print(f"  {name:12} {curr:>10,.0f}  {direction} {chg:+6.2f}%", file=out_stream)

        # TOP LARGE CAP STOCKS
        print("\nTOP 10 LARGE-CAP STOCKS", file=out_stream)
        print("-" * 70, file=out_stream)

        universe = [
            "MSFT","AAPL","NVDA","AMZN","GOOGL",
            "META","BRK-B","TSLA","AVGO","V",
            "LLY","JPM","XOM","UNH","MA"
        ]

        results = []
        for ticker in universe:
            st = yf.download(ticker, period="5d", progress=False)
            if not st.empty:
                curr = st["Close"].iloc[-1].item()
                prev = st["Close"].iloc[-2].item()
                chg = ((curr - prev) / prev) * 100
                results.append((ticker, curr, chg))

        results.sort(key=lambda x: abs(x[2]), reverse=True)

        for ticker, price, chg in results[:10]:
            direction = "↑" if chg >= 0 else "↓"
            print(f"  {ticker:6} ${price:>9,.2f}  {direction} {chg:+6.2f}%", file=out_stream)

        print("\n" + "=" * 70, file=out_stream)

    except Exception as e:
        print(f"Error: {e}", file=out_stream)
        import traceback
        traceback.print_exc()


def send_email(content):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_ADDRESS
    msg["Subject"] = f"Daily Brief - {datetime.now().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText(content, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        print("Email sent successfully.")


if __name__ == "__main__":
    # Capture all printed output
    buffer = io.StringIO()
    get_briefing(buffer)
    content = buffer.getvalue()
    buffer.close()

    # Send via email
    send_email(content)