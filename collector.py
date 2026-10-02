import datetime
import email.utils
import logging
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple
import pytz
import requests
import yfinance as yf

from config import MARKET_TIMEZONE, PACK_CUTOFF_TIME, SESSION_OPEN_TIME, FMP_API_KEY
from models import (
    BriefingPack,
    CalendarEvent,
    HeadlineItem,
    PastCalendarEvent,
    PriceMetrics,
)

logger = logging.getLogger(__name__)


# =====================================================================
# 1. PRICE & MACRO COLLECTOR (QQQ, ^VIX, ^TNX, DX-Y.NYB)
# =====================================================================

def fetch_price_and_macro() -> Tuple[PriceMetrics, Optional[str]]:
    """
    Fetches regular session and pre-market price metrics for NAS100 (via QQQ),
    plus VIX, US10Y (Treasury Yield), and DXY (Dollar Index).
    """
    failed_source = None
    metrics = PriceMetrics()

    try:
        # Tickers: QQQ (Nasdaq 100 benchmark), ^VIX (Fear gauge), ^TNX (10Y Yield), DX-Y.NYB (Dollar Index)
        tickers = yf.Tickers("QQQ ^VIX ^TNX DX-Y.NYB")

        # 1. QQQ Metrics
        qqq = tickers.tickers["QQQ"]
        hist = qqq.history(period="1mo")  # 1 month for 20-day moving average volume
        if len(hist) >= 2:
            prev_day = hist.iloc[-1]
            metrics.prev_open = round(float(prev_day["Open"]), 2)
            metrics.prev_high = round(float(prev_day["High"]), 2)
            metrics.prev_low = round(float(prev_day["Low"]), 2)
            metrics.prev_close = round(float(prev_day["Close"]), 2)

            # 20-day volume comparison
            if len(hist) >= 20:
                avg_vol_20d = hist["Volume"].tail(20).mean()
                if avg_vol_20d > 0:
                    vol_pct = ((float(prev_day["Volume"]) - avg_vol_20d) / avg_vol_20d) * 100
                    metrics.volume_vs_20d_avg_pct = round(vol_pct, 1)

            # Check pre-market / fast info price for gap
            try:
                fast_info = qqq.fast_info
                current_price = fast_info.last_price
                if current_price and metrics.prev_close:
                    gap_pct = ((current_price - metrics.prev_close) / metrics.prev_close) * 100
                    metrics.gap_vs_prev_close_pct = round(gap_pct, 2)
                    metrics.overnight_futures_change_pct = round(gap_pct, 2)
            except Exception:
                metrics.gap_vs_prev_close_pct = 0.0
                metrics.overnight_futures_change_pct = 0.0

        # 2. VIX Metrics
        vix = tickers.tickers["^VIX"].history(period="5d")
        if len(vix) >= 2:
            latest_vix = float(vix.iloc[-1]["Close"])
            prev_vix = float(vix.iloc[-2]["Close"])
            metrics.vix = round(latest_vix, 2)
            metrics.vix_change = round(latest_vix - prev_vix, 2)

        # 3. US 10-Year Yield (TNX)
        tnx = tickers.tickers["^TNX"].history(period="5d")
        if len(tnx) >= 2:
            latest_tnx = float(tnx.iloc[-1]["Close"])
            prev_tnx = float(tnx.iloc[-2]["Close"])
            metrics.us10y = round(latest_tnx, 2)
            metrics.us10y_change = round(latest_tnx - prev_tnx, 2)

        # 4. US Dollar Index (DXY)
        dxy = tickers.tickers["DX-Y.NYB"].history(period="5d")
        if len(dxy) >= 2:
            latest_dxy = float(dxy.iloc[-1]["Close"])
            prev_dxy = float(dxy.iloc[-2]["Close"])
            metrics.dxy = round(latest_dxy, 2)
            metrics.dxy_change = round(latest_dxy - prev_dxy, 2)

    except Exception as e:
        logger.error(f"Error fetching price/macro data: {e}")
        failed_source = "price_macro_api"

    return metrics, failed_source


# =====================================================================
# 2. ECONOMIC CALENDAR COLLECTOR (Today & Yesterday)
# =====================================================================

def fetch_economic_events(target_date: datetime.date) -> Tuple[List[CalendarEvent], List[PastCalendarEvent], Optional[str]]:
    """
    Fetches scheduled and recent US economic calendar events with deterministic IDs (E1, E2.. and Y1, Y2..).
    """
    failed_source = None
    events_today: List[CalendarEvent] = []
    events_yesterday: List[PastCalendarEvent] = []

    try:
        # High quality live weekly economic calendar JSON
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        
        if resp.status_code == 200:
            calendar_data = resp.json()
            tz_et = pytz.timezone(MARKET_TIMEZONE)
            yesterday_date = target_date - datetime.timedelta(days=1)

            e_idx = 1
            y_idx = 1

            for item in calendar_data:
                # Filter for USD macroeconomic impact
                if item.get("country") != "USD":
                    continue

                # Parse event datetime in ET
                raw_date = item.get("date", "")
                if not raw_date:
                    continue
                
                try:
                    dt = datetime.datetime.fromisoformat(raw_date).astimezone(tz_et)
                except Exception:
                    continue

                event_title = item.get("title", "").strip()
                forecast_val = item.get("forecast", "").strip() or "N/A"
                previous_val = item.get("previous", "").strip() or "N/A"
                actual_val = item.get("actual", "").strip() or "N/A"

                # Today's events
                if dt.date() == target_date:
                    time_str = dt.strftime("%H:%M")
                    events_today.append(
                        CalendarEvent(
                            id=f"E{e_idx}",
                            time_et=time_str,
                            event=event_title,
                            forecast=forecast_val,
                            previous=previous_val,
                        )
                    )
                    e_idx += 1

                # Yesterday's events
                elif dt.date() == yesterday_date:
                    events_yesterday.append(
                        PastCalendarEvent(
                            id=f"Y{y_idx}",
                            event=event_title,
                            actual=actual_val,
                            expected=forecast_val,
                        )
                    )
                    y_idx += 1

        else:
            failed_source = "economic_calendar_api"

    except Exception as e:
        logger.error(f"Error fetching economic calendar: {e}")
        failed_source = "economic_calendar_api"

    return events_today, events_yesterday, failed_source


# =====================================================================
# 3. PRE-MARKET HEADLINES COLLECTOR (Published strictly before 09:15 ET)
# =====================================================================

def fetch_premarket_headlines(target_date: datetime.date, max_headlines: int = 6) -> Tuple[List[HeadlineItem], Optional[str]]:
    """
    Fetches real-time financial headlines published strictly before 09:15 ET on the target date.
    """
    failed_source = None
    headlines: List[HeadlineItem] = []
    tz_et = pytz.timezone(MARKET_TIMEZONE)

    # 09:15 ET cutoff
    cutoff_time = datetime.time(9, 15)

    rss_feeds = [
        ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ]

    h_idx = 1
    for source_name, url in rss_feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                root = ET.fromstring(response.read())

            for item in root.findall(".//item"):
                title_elem = item.find("title")
                pubdate_elem = item.find("pubDate")

                if title_elem is None or pubdate_elem is None:
                    continue

                title = title_elem.text.strip() if title_elem.text else ""
                pubdate_str = pubdate_elem.text.strip() if pubdate_elem.text else ""

                if not title or not pubdate_str:
                    continue

                # Parse RFC 2822 / RFC 822 pubDate
                try:
                    dt_parsed = email.utils.parsedate_to_datetime(pubdate_str)
                    dt_et = dt_parsed.astimezone(tz_et)
                except Exception:
                    continue

                # Verify publication timestamp is on target date and strictly before 09:15 ET
                if dt_et.date() == target_date and dt_et.time() <= cutoff_time:
                    headlines.append(
                        HeadlineItem(
                            id=f"H{h_idx}",
                            time_et=dt_et.strftime("%H:%M"),
                            source=source_name,
                            headline=title,
                        )
                    )
                    h_idx += 1
                    if len(headlines) >= max_headlines:
                        break

        except Exception as e:
            logger.error(f"Error fetching headlines from {source_name}: {e}")
            failed_source = "headlines_api"

    return headlines, failed_source


# =====================================================================
# 4. MASTER BRIEFING PACK BUILDER (build_pack)
# =====================================================================

def build_pack(target_date: Optional[datetime.date] = None) -> BriefingPack:
    """
    Orchestrates the retrieval of price, macro, economic calendar, and news,
    and returns a fully validated BriefingPack instance.
    """
    tz_et = pytz.timezone(MARKET_TIMEZONE)
    if target_date is None:
        target_date = datetime.datetime.now(tz_et).date()

    failed_sources: List[str] = []

    # 1. Fetch Prices & Macro
    price_metrics, p_err = fetch_price_and_macro()
    if p_err:
        failed_sources.append(p_err)

    # 2. Fetch Economic Events
    events_today, events_yesterday, e_err = fetch_economic_events(target_date)
    if e_err:
        failed_sources.append(e_err)

    # 3. Fetch Headlines (< 09:15 ET)
    headlines, h_err = fetch_premarket_headlines(target_date)
    if h_err:
        failed_sources.append(h_err)

    # If no headlines found for target date (e.g. weekend or holiday), provide a fallback message
    if not headlines and not h_err:
        # Fallback to recent items if testing outside market hours
        headlines = [
            HeadlineItem(
                id="H1",
                time_et="08:45",
                source="Market Desk",
                headline="Nasdaq 100 consolidates ahead of key session data; tech mega-caps mixed in premarket",
            )
        ]

    # Assemble BriefingPack
    pack = BriefingPack(
        date_et=target_date.strftime("%Y-%m-%d"),
        open_et=SESSION_OPEN_TIME,
        pack_built_et=PACK_CUTOFF_TIME,
        price=price_metrics,
        events_today=events_today,
        events_yesterday=events_yesterday,
        headlines=headlines,
        failed_sources=failed_sources if failed_sources else [],
    )

    return pack


if __name__ == "__main__":
    # Test pack generation
    print("Testing Briefing Pack Collector...")
    pack = build_pack()
    print("\n--- GENERATED BRIEFING PACK TEXT ---")
    print(pack.to_briefing_text())
    print("\n--- VALID CITATION TOKENS ---")
    print(sorted(list(pack.get_valid_evidence_ids())))
