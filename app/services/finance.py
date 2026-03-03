import io
import math
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import requests
import yfinance as yf
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class FinanceDataError(Exception):
    """Raised when finance data cannot be resolved."""


_ANALYSIS_CACHE: dict[tuple[str, ...], tuple[float, "AnalysisResult"]] = {}
_CACHE_TTL_SECONDS = 900
_YAHOO_SPARK_URLS = (
    "https://query1.finance.yahoo.com/v7/finance/spark",
    "https://query2.finance.yahoo.com/v7/finance/spark",
)
_YAHOO_SPARK_BASE_PARAMS = {
    "range": "10y",
    "interval": "1d",
}
_YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def _chunked_symbols(tickers: list[str], size: int = 6) -> list[list[str]]:
    return [tickers[index : index + size] for index in range(0, len(tickers), size)]


def clean_tickers(raw_tickers: list[str] | str) -> list[str]:
    if isinstance(raw_tickers, str):
        tokens = raw_tickers.replace("\n", ",").replace(" ", ",").split(",")
    else:
        tokens = raw_tickers

    cleaned: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        ticker = token.strip().upper()
        if not ticker:
            continue
        if ticker in seen:
            continue
        seen.add(ticker)
        cleaned.append(ticker)
    return cleaned


def _fetch_spark_series(tickers: list[str]) -> dict[str, pd.Series]:
    last_error: Exception | None = None

    for attempt in range(4):
        price_map: dict[str, pd.Series] = {}
        for symbol_group in _chunked_symbols(tickers, size=6):
            group_error: Exception | None = None
            for spark_url in _YAHOO_SPARK_URLS:
                params = {**_YAHOO_SPARK_BASE_PARAMS, "symbols": ",".join(symbol_group)}
                try:
                    response = requests.get(
                        spark_url,
                        params=params,
                        headers=_YAHOO_HEADERS,
                        timeout=20,
                    )

                    if response.status_code == 429:
                        raise FinanceDataError("Yahoo Finance rate-limited the request.")

                    response.raise_for_status()
                    payload = response.json()
                    spark = payload.get("spark", {})
                    results = spark.get("result") or []
                    if not results:
                        raise FinanceDataError("No Yahoo Finance results were returned.")

                    for result in results:
                        symbol = str(result.get("symbol", "")).upper()
                        response_rows = result.get("response") or []
                        if not symbol or not response_rows:
                            continue

                        row = response_rows[0]
                        timestamps = row.get("timestamp") or []
                        quote = (row.get("indicators", {}).get("quote") or [{}])[0]
                        closes = quote.get("close") or []
                        if not timestamps or not closes:
                            continue

                        length = min(len(timestamps), len(closes))
                        index = pd.to_datetime(timestamps[:length], unit="s", utc=True).tz_localize(
                            None
                        )
                        series = pd.Series(closes[:length], index=index, name=symbol).dropna()
                        if series.empty:
                            continue
                        price_map[symbol] = series

                    group_error = None
                    break
                except Exception as exc:
                    group_error = exc
                    last_error = exc

            if group_error:
                last_error = group_error

            time.sleep(0.15)

        if price_map:
            return price_map

        backoff_seconds = (2**attempt) + random.uniform(0.25, 0.7)  # nosec B311
        time.sleep(backoff_seconds)

    message = str(last_error) if last_error else "Unknown Yahoo Finance error."
    raise FinanceDataError(f"Unable to retrieve data from Yahoo Finance: {message}") from last_error


def _extract_close_from_yf_download(frame: pd.DataFrame, ticker: str) -> pd.Series:
    if frame.empty:
        raise FinanceDataError(
            f"No 10-year history found for {ticker}, or Yahoo temporarily blocked this symbol."
        )

    if isinstance(frame.columns, pd.MultiIndex):
        if "Close" in frame.columns.get_level_values(0):
            close = frame["Close"][ticker]
        elif "Adj Close" in frame.columns.get_level_values(0):
            close = frame["Adj Close"][ticker]
        else:
            raise FinanceDataError(f"Close price data is unavailable for {ticker}.")
    else:
        if "Close" in frame.columns:
            close = frame["Close"]
        elif "Adj Close" in frame.columns:
            close = frame["Adj Close"]
        else:
            raise FinanceDataError(f"Close price data is unavailable for {ticker}.")
    return close.dropna().rename(ticker)


def _fetch_single_yfinance_series(ticker: str) -> pd.Series:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            history = yf.Ticker(ticker).history(period="10y", auto_adjust=True)
            if not history.empty and "Close" in history.columns:
                close = history["Close"].dropna()
                if not close.empty:
                    try:
                        close.index = close.index.tz_localize(None)
                    except TypeError:
                        pass
                    return close.rename(ticker)
        except Exception as exc:
            last_error = exc

        try:
            download_frame = yf.download(
                ticker,
                period="10y",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            close = _extract_close_from_yf_download(download_frame, ticker)
            try:
                close.index = close.index.tz_localize(None)
            except TypeError:
                pass
            return close
        except Exception as exc:
            last_error = exc

        time.sleep((2**attempt) + random.uniform(0.2, 0.6))  # nosec B311

    message = str(last_error) if last_error else "Unknown Yahoo Finance error."
    raise FinanceDataError(f"Unable to retrieve data for {ticker}: {message}") from last_error


def _build_price_frame(tickers: list[str]) -> tuple[pd.DataFrame, dict[str, str]]:
    price_series: list[pd.Series] = []
    excluded_details: dict[str, str] = {}
    series_map: dict[str, pd.Series] = {}
    spark_error: str | None = None

    try:
        series_map = _fetch_spark_series(tickers)
    except Exception as exc:
        spark_error = str(exc)

    for ticker in tickers:
        series = series_map.get(ticker)
        if series is not None:
            price_series.append(series.rename(ticker))
            continue

        # Fallback to yfinance per symbol when the spark API is throttled or partial.
        try:
            fallback_series = _fetch_single_yfinance_series(ticker)
            price_series.append(fallback_series.rename(ticker))
        except Exception as exc:
            reason = str(exc)
            if spark_error:
                reason = f"{reason} | Spark API: {spark_error}"
            excluded_details[ticker] = reason

    if not price_series:
        error_details = " | ".join(f"{ticker}: {reason}" for ticker, reason in excluded_details.items())
        raise FinanceDataError(
            "No valid tickers found. Confirm symbols exist on Yahoo Finance and try again. "
            f"Details: {error_details}"
        )

    frame = pd.concat(price_series, axis=1).sort_index()
    return frame, excluded_details


def _align_prices_for_comparison(
    price_frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    first_valid = []
    for column in price_frame.columns:
        first_index = price_frame[column].first_valid_index()
        if first_index is not None:
            first_valid.append(first_index)

    if not first_valid:
        raise FinanceDataError("Insufficient overlap to compare tickers.")

    common_start = max(first_valid)
    aligned = price_frame.loc[common_start:].ffill().dropna(how="any")

    if aligned.empty or aligned.shape[0] < 2:
        raise FinanceDataError(
            "Tickers do not share enough overlapping history for a representative comparison."
        )

    normalized = aligned.div(aligned.iloc[0]).mul(100.0)
    common_end = aligned.index[-1]
    return aligned, normalized, common_start, common_end


def _calculate_metrics(aligned_prices: pd.DataFrame) -> list[dict[str, float | str]]:
    metrics: list[dict[str, float | str]] = []

    for ticker in aligned_prices.columns:
        prices = aligned_prices[ticker]
        daily_returns = prices.pct_change().dropna()

        total_return = (prices.iloc[-1] / prices.iloc[0] - 1.0) * 100.0
        elapsed_years = max((prices.index[-1] - prices.index[0]).days / 365.25, 0.0001)
        cagr = ((prices.iloc[-1] / prices.iloc[0]) ** (1.0 / elapsed_years) - 1.0) * 100.0
        annual_volatility = (
            daily_returns.std(ddof=0) * math.sqrt(252.0) * 100.0
            if not daily_returns.empty
            else 0.0
        )
        drawdown = prices.div(prices.cummax()).sub(1.0)
        max_drawdown = drawdown.min() * 100.0

        metrics.append(
            {
                "ticker": ticker,
                "start_price": round(float(prices.iloc[0]), 2),
                "end_price": round(float(prices.iloc[-1]), 2),
                "total_return_pct": round(float(total_return), 2),
                "cagr_pct": round(float(cagr), 2),
                "annualized_volatility_pct": round(float(annual_volatility), 2),
                "max_drawdown_pct": round(float(max_drawdown), 2),
                "ending_value_of_10000": round(float(10000.0 * (1.0 + total_return / 100.0)), 2),
            }
        )

    metrics.sort(key=lambda row: row["total_return_pct"], reverse=True)
    return metrics


def _downsample_for_chart(normalized_prices: pd.DataFrame) -> pd.DataFrame:
    weekly = normalized_prices.resample("W-FRI").last().dropna(how="any")
    if weekly.shape[0] >= 80:
        return weekly
    return normalized_prices.dropna(how="any")


@dataclass
class AnalysisResult:
    requested_tickers: list[str]
    excluded_details: dict[str, str]
    aligned_prices: pd.DataFrame
    normalized_prices: pd.DataFrame
    chart_prices: pd.DataFrame
    metrics: list[dict[str, float | str]]
    common_start: pd.Timestamp
    common_end: pd.Timestamp
    generated_at: datetime

    @property
    def included_tickers(self) -> list[str]:
        return self.aligned_prices.columns.tolist()

    def to_payload(self) -> dict:
        timeline = [timestamp.strftime("%Y-%m-%d") for timestamp in self.chart_prices.index]
        chart_series = {
            ticker: [round(float(value), 4) for value in self.chart_prices[ticker].tolist()]
            for ticker in self.chart_prices.columns
        }
        return {
            "analysis_timestamp_utc": self.generated_at.isoformat(),
            "requested_tickers": self.requested_tickers,
            "included_tickers": self.included_tickers,
            "excluded_tickers": list(self.excluded_details.keys()),
            "excluded_details": self.excluded_details,
            "common_start_date": self.common_start.strftime("%Y-%m-%d"),
            "common_end_date": self.common_end.strftime("%Y-%m-%d"),
            "metrics": self.metrics,
            "chart": {"timeline": timeline, "series": chart_series},
        }


def analyze_tickers(tickers: list[str] | str) -> AnalysisResult:
    cleaned_tickers = clean_tickers(tickers)
    if not cleaned_tickers:
        raise FinanceDataError("Provide at least one valid ticker.")

    cache_key = tuple(cleaned_tickers)
    now_ts = time.time()
    cached_result = _ANALYSIS_CACHE.get(cache_key)
    if cached_result and now_ts - cached_result[0] <= _CACHE_TTL_SECONDS:
        return cached_result[1]

    price_frame, excluded_details = _build_price_frame(cleaned_tickers)
    aligned, normalized, common_start, common_end = _align_prices_for_comparison(price_frame)

    chart_frame = _downsample_for_chart(normalized)
    metrics = _calculate_metrics(aligned)

    result = AnalysisResult(
        requested_tickers=cleaned_tickers,
        excluded_details=excluded_details,
        aligned_prices=aligned,
        normalized_prices=normalized,
        chart_prices=chart_frame,
        metrics=metrics,
        common_start=common_start,
        common_end=common_end,
        generated_at=datetime.now(timezone.utc),
    )
    _ANALYSIS_CACHE[cache_key] = (now_ts, result)
    return result


def _create_chart_image(chart_prices: pd.DataFrame) -> io.BytesIO:
    figure, axis = plt.subplots(figsize=(10.5, 4.6), dpi=160)

    for ticker in chart_prices.columns:
        axis.plot(
            chart_prices.index,
            chart_prices[ticker].values,
            linewidth=2.0,
            label=ticker,
        )

    axis.set_title("Normalized 10-Year Growth (Base = 100)")
    axis.set_ylabel("Growth Index")
    axis.grid(alpha=0.25, linestyle="--")
    axis.legend(loc="upper left", ncol=min(4, max(1, len(chart_prices.columns))))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    figure.autofmt_xdate()
    figure.tight_layout()

    image_buffer = io.BytesIO()
    figure.savefig(image_buffer, format="png")
    image_buffer.seek(0)
    plt.close(figure)
    return image_buffer


def build_pdf_report(analysis: AnalysisResult, report_title: str | None = None) -> bytes:
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(letter),
        rightMargin=28,
        leftMargin=28,
        topMargin=28,
        bottomMargin=28,
    )

    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading1"],
        fontSize=19,
        textColor=colors.HexColor("#0d2a4b"),
        spaceAfter=8,
    )
    text_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=10,
        textColor=colors.HexColor("#2e3a47"),
        leading=13,
    )

    title = report_title or "Financial Modeling Report"
    subtitles = (
        f"Tickers: {', '.join(analysis.included_tickers)}<br/>"
        f"Comparison window: {analysis.common_start.strftime('%b %d, %Y')} "
        f"to {analysis.common_end.strftime('%b %d, %Y')}<br/>"
        f"Generated (UTC): {analysis.generated_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    content: list = [Paragraph(title, heading_style), Paragraph(subtitles, text_style), Spacer(1, 12)]

    chart_image = _create_chart_image(analysis.chart_prices)
    content.append(RLImage(chart_image, width=705, height=300))
    content.append(Spacer(1, 12))

    table_rows: list[list[str]] = [
        [
            "Ticker",
            "Total Return",
            "CAGR",
            "Ann. Volatility",
            "Max Drawdown",
            "Start Price",
            "End Price",
            "$10K Ending Value",
        ]
    ]

    for row in analysis.metrics:
        table_rows.append(
            [
                str(row["ticker"]),
                f"{row['total_return_pct']:.2f}%",
                f"{row['cagr_pct']:.2f}%",
                f"{row['annualized_volatility_pct']:.2f}%",
                f"{row['max_drawdown_pct']:.2f}%",
                f"${row['start_price']:.2f}",
                f"${row['end_price']:.2f}",
                f"${row['ending_value_of_10000']:.2f}",
            ]
        )

    summary_table = Table(table_rows, repeatRows=1)
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d2a4b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6fa")]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#a7b6c6")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    content.append(summary_table)
    content.append(Spacer(1, 10))

    if analysis.excluded_details:
        excluded_text = "<br/>".join(
            f"{ticker}: {reason}" for ticker, reason in analysis.excluded_details.items()
        )
        content.append(
            Paragraph(
                f"Excluded tickers due to missing data:<br/>{excluded_text}",
                text_style,
            )
        )

    content.append(
        Spacer(1, 10)
    )
    content.append(
        Paragraph(
            "Data source: Yahoo Finance. Figures are historical and for informational use only.",
            text_style,
        )
    )

    document.build(content)
    output.seek(0)
    return output.read()
