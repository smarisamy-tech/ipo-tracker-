# True Live Mainboard IPO Dashboard

This version contains **no demo IPO dataset**. Every dashboard load calls the backend, which fetches InvestorGain's current Mainboard subscription report. IPOs with subscription >= 100x are then checked against their InvestorGain GMP page. Only latest estimated profit > ₹500 qualifies.

## Run on Windows

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Deploy to Render

Push these files to GitHub, create a Render Web Service, or use the included `render.yaml`.

Build:
`pip install -r requirements.txt`

Start:
`gunicorn app:app --workers 1 --threads 4 --timeout 90`

## Live behavior

- Fetches current Mainboard subscription table from InvestorGain.
- Excludes SME by source route.
- Rejects subscription < 100x.
- Opens the linked InvestorGain GMP page for remaining IPOs.
- Reads the latest GMP row, estimated listing price, estimated profit and trend.
- Requires estimated profit > ₹500.
- Browser auto-refreshes every 60 seconds; backend caches for 60 seconds.
- Manual Refresh Live bypasses cache.

If InvestorGain changes its HTML or blocks server-side requests, diagnostics will show the parsing/request error.

## Fix v2
GMP URLs are now derived from InvestorGain subscription links using the same slug and IPO ID. This fixes missing GMP links and malformed IPO names.
