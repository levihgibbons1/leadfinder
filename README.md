# LeadFinder

LeadFinder is a Streamlit app for finding under-served blue-collar businesses in smaller towns, analyzing their websites for strong redesign signals, and saving the results for follow-up.

## Stack

- Python + Streamlit
- RapidAPI local business search
- `requests` + BeautifulSoup website analysis
- OpenAI Responses API for signal/opener enrichment
- pandas + openpyxl for Excel export
- SQLite locally or hosted Postgres/Supabase for shared lead history

## Quick Start

1. Create a virtual environment and install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add your API keys.

3. Start the app:

   ```bash
   streamlit run app.py
   ```

## Project Structure

```text
.
├── app.py
├── data/
├── leadfinder/
│   ├── config.py
│   ├── database.py
│   ├── excel.py
│   ├── models.py
│   ├── pipeline.py
│   ├── utils.py
│   └── services/
│       ├── ai_enrichment.py
│       ├── business_search.py
│       └── website_analyzer.py
├── requirements.txt
└── .env.example
```

## Notes

- New leads are upserted into `data/leads.db`.
- The Excel workbook is kept at `data/leads.xlsx`.
- Duplicate protection uses a hash of business name, phone, website, and location.
- If `OPENAI_API_KEY` is missing, the app falls back to rule-based signals and openers.

## Hosted Database

For a public team app, set `DATABASE_URL` to a hosted Postgres connection string from Supabase.
If `DATABASE_URL` is blank, the app uses local SQLite.

Use the Supabase pooled connection string when deploying to Streamlit Community Cloud, Render, or Railway.

See `DEPLOYMENT.md` for the recommended Supabase + Streamlit Cloud setup.
