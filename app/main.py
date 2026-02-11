from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.services.finance import (
    FinanceDataError,
    analyze_tickers,
    build_pdf_report,
    clean_tickers,
)


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Financial Modeling Platform",
    description="10-year performance modeling for stocks, ETFs, and mutual funds using Yahoo Finance.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class AnalyzeRequest(BaseModel):
    tickers: list[str] | str = Field(
        ...,
        description="Ticker symbols as an array or comma-separated string.",
    )


class PDFRequest(AnalyzeRequest):
    report_title: str | None = Field(
        default=None,
        description="Optional custom title for the exported PDF report.",
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(payload: AnalyzeRequest) -> dict:
    tickers = clean_tickers(payload.tickers)
    if not tickers:
        raise HTTPException(status_code=400, detail="Provide at least one ticker.")

    try:
        result = analyze_tickers(tickers)
    except FinanceDataError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc

    return result.to_payload()


@app.post("/api/report/pdf")
async def report_pdf(payload: PDFRequest) -> Response:
    tickers = clean_tickers(payload.tickers)
    if not tickers:
        raise HTTPException(status_code=400, detail="Provide at least one ticker.")

    try:
        result = analyze_tickers(tickers)
        pdf_bytes = build_pdf_report(result, report_title=payload.report_title)
    except FinanceDataError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc

    filename_slug = "-".join(tickers[:5]).lower()
    filename = f"financial-report-{filename_slug or 'analysis'}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

