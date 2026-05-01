# Deploy LeadFinder

This is the recommended first production setup:

- App host: Streamlit Community Cloud
- Database: Supabase Postgres
- Secrets: Streamlit app secrets

## 1. Create Supabase Database

1. Create a Supabase project.
2. Open Project Settings.
3. Go to Database.
4. Copy the pooled Postgres connection string.
5. Replace `[YOUR-PASSWORD]` with the database password you set when creating the project.

Use the pooled connection string for hosted Streamlit. It should look similar to:

```text
postgresql://postgres.[project-ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

LeadFinder creates the `leads` table automatically on first run.

## 2. Push LeadFinder To GitHub

Streamlit Community Cloud deploys from GitHub. Keep `.env` out of GitHub.

The required app entrypoint is:

```text
app.py
```

## 3. Deploy On Streamlit Community Cloud

1. Go to Streamlit Community Cloud.
2. Create a new app.
3. Select the GitHub repo.
4. Set the entrypoint to `app.py`.
5. Add secrets in the Advanced settings panel.

Use this format:

```toml
DATABASE_URL = "postgresql://postgres.[project-ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
RAPIDAPI_KEY = "your_rapidapi_key"
RAPIDAPI_HOST = "local-business-data.p.rapidapi.com"
RAPIDAPI_BASE_URL = "https://local-business-data.p.rapidapi.com"
RAPIDAPI_TIMEOUT_SECONDS = "25"
OPENAI_API_KEY = "your_openai_key"
OPENAI_MODEL = "gpt-4o-mini"
REQUEST_TIMEOUT_SECONDS = "10"
APP_PASSWORD = "vanguardcreatives"
```

## 4. Share The URL

After deployment, Streamlit gives you a public `streamlit.app` URL. Anyone with the URL can open the app unless you enable Streamlit app access controls.

## Notes

- Local development still uses `data/leads.db` when `DATABASE_URL` is blank.
- Hosted deployment uses Supabase when `DATABASE_URL` is present.
- The local `.env` file should never be committed.
