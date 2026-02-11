# Financial Modeling Platform

Commercial-ready web platform for 10-year historical performance modeling across:
- Single stocks
- ETFs
- Mutual funds

The app pulls data from Yahoo Finance, normalizes performance for representative comparison, and exports a printable PDF report.

## Tech Stack
- FastAPI backend
- Custom HTML/CSS/JavaScript frontend
- Yahoo Finance data via direct Yahoo spark API requests
- PDF generation via `reportlab`

## Features
- Multi-ticker input with support for stocks, ETFs, and mutual funds
- 10-year normalized growth comparison chart
- Key analytics:
  - Total return
  - CAGR
  - Annualized volatility
  - Max drawdown
  - Ending value of a hypothetical `$10,000`
- Downloadable PDF report optimized for printing/sharing
- Responsive UI for desktop and mobile

## Run Locally

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
uvicorn app.main:app --reload
```

4. Open:

```text
http://127.0.0.1:8000
```

## API Endpoints
- `POST /api/analyze` - returns modeled performance and metrics
- `POST /api/report/pdf` - returns a printable PDF report
- `GET /health` - health check

## Notes
- Data source is Yahoo Finance and may have gaps for delisted/incomplete symbols.
- The platform is for analysis/reporting and does not provide investment advice.
