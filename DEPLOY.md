# Deploy OptionsELI on Streamlit Community Cloud

This guide prepares a public, anonymous, read-only website. Do not place `.env`,
`data/optionseli.db`, `.streamlit/secrets.toml`, API tokens, or account IDs in Git.

## What public mode changes

When `OPTIONSELI_PUBLIC_MODE = true` is set in Streamlit secrets:

- Market Overview, Stock Scanner, Options Scanner, and Testing Lab remain public.
- Settings and Trade Journal are removed from navigation.
- SQLite is not opened by the web app.
- Visitors cannot view, enter, test, or change Tradier credentials or server settings.
- The options client remains read-only and exposes no brokerage/order endpoints.
- Public Tradier display is disabled by default because personal API data cannot be
  redistributed. The options scanner remains available with labeled demonstration data.
- Tradier expiration responses are cached for 15 minutes and chains for 5 minutes.
- Shared upstream cache misses are rate-limited and each scan checks at most four expirations.

The local application remains unchanged when `OPTIONSELI_PUBLIC_MODE=false`.

## 1. Security preflight

From the project folder, confirm sensitive files are ignored:

```bash
cd "/path/to/OptionsELI"
git check-ignore .env data/optionseli.db .venv .streamlit/secrets.toml
git status --short --ignored
```

The first command must list all four paths. Never use `git add -f` on them. If a
secret was ever committed, rotate the token before publishing; `.gitignore` does not
remove secrets from Git history.

Recommended repository contents include `app.py`, `streamlit_app.py`, `optionseli/`, `requirements.txt`,
`.python-version`, `.streamlit/config.toml`, tests, README, and this guide. The file
`.streamlit/secrets.toml.example` contains names only and no real credentials.

## 2. Test public mode locally without copying your token

The automated tests exercise public navigation and secret precedence:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Your ordinary local launcher continues to use `.env` and keeps the journal enabled.

## 3. Create and push a GitHub repository

Create an empty GitHub repository named `OptionsELI`. A public repository is simplest
for an anonymous public app. Then run the commands GitHub shows for an existing local
repository. A typical first push is:

```bash
git add .gitignore .python-version .streamlit/config.toml \
  .streamlit/secrets.toml.example app.py streamlit_app.py optionseli tests \
  requirements.txt requirements-dev.txt README.md PLAN.md DEPLOY.md
git commit -m "Prepare OptionsELI for public Streamlit deployment"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/OptionsELI.git
git push -u origin main
```

Review the staged file list with `git diff --cached --name-only` before committing.
It must not include `.env`, `.venv`, `.python`, `.tools`, `data/optionseli.db`, or a
real `secrets.toml`.

## 4. Create the Streamlit app

1. Sign in at [share.streamlit.io](https://share.streamlit.io/) and connect GitHub.
2. Select **Create app** and **Yup, I have an app**.
3. Select the `OptionsELI` repository, branch `main`, and entrypoint
   `streamlit_app.py`. This dedicated entrypoint forces public read-only mode even if
   the public-mode secret is accidentally omitted. Do not deploy `app.py` directly.
4. Open **Advanced settings** and select Python **3.12**.
5. In **Secrets**, use this public-safe configuration. Do not add a personal Tradier
   token for anonymous redistribution:

   ```toml
   OPTIONSELI_PUBLIC_MODE = true
   OPTIONSELI_DEMO_MODE = true
   OPTIONSELI_PUBLIC_TRADIER_AUTHORIZED = false
   OPTIONSELI_API_CALLS_PER_MINUTE = 50
   OPTIONSELI_MAX_EXPIRATIONS_PER_SCAN = 4
   ```

   Do not add `TRADIER_API_TOKEN` or `TRADIER_ACCOUNT_ID`, and do not paste the local
   `.env` file. Tradier says non-Partner API access is personal-only and market data
   cannot be redistributed to people without active Tradier accounts. If Tradier
   later grants the required Partner/data-display authorization, follow its OAuth
   and display requirements before setting `OPTIONSELI_PUBLIC_TRADIER_AUTHORIZED = true`.
6. Save the advanced settings and deploy.

Streamlit documents that Community Cloud reads dependencies from the repository,
supports Python 3.12, and stores secrets in the app's server-side settings rather
than the Git repository.

## 5. Make access anonymous

After deployment, open **App settings → Sharing** and choose **This app is public and
searchable**. A public app can then be opened from its `*.streamlit.app` URL without
an account or password. Verify this in a private/incognito browser window.

## 6. Post-deployment checks

- Market Overview loads and labels Yahoo data as delayed/cached where applicable.
- Stock Scanner works for the predefined liquid universe.
- Options Scanner displays demonstration labels and evaluates both spread directions.
- Public Tradier data stays blocked unless Partner authorization is explicitly enabled.
- Missing Greeks are explicitly reported and excluded.
- Settings and Trade Journal do not appear anywhere in navigation.
- Repeated scans return cached results or a friendly rate-limit message.
- No token, account ID, `.env` contents, or authorization headers appear in the UI or logs.
- No order-entry or brokerage execution control exists.

Do not enable public Tradier display merely because a token works. Partner/data-use
authorization is a separate requirement.

## 7. Updating the site

Push reviewed commits to `main`; Community Cloud redeploys repository changes. Update
or rotate credentials only through **App settings → Secrets**. Keep the local `.env`
and SQLite journal private and backed up separately.

Official references:

- [Deploy an app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Public sharing settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)
