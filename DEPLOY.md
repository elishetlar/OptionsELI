# Deploy OptionsELI as a private single-user Streamlit app

This configuration uses two independent access controls:

1. Streamlit Community Cloud sharing is set to **Only specific people can view this app**.
2. OptionsELI uses Streamlit OIDC and an email allowlist before `app.py` or any market-data client is loaded.

Never commit `.env`, `data/optionseli.db`, `.streamlit/secrets.toml`, credentials,
OAuth client secrets, cookie secrets, or virtual environments.

## Tradier permission gate

Tradier's published documentation says non-Partner API access is for personal use
and that market data cannot be redistributed to people without active Tradier
accounts. It does not clearly state whether a personal token may be used from a
private, single-user cloud host. Authentication alone does not decide data licensing.

Until Tradier provides explicit written approval for this exact use case, keep:

```toml
OPTIONSELI_PUBLIC_TRADIER_AUTHORIZED = false
OPTIONSELI_PRIVATE_CLOUD_TRADIER_AUTHORIZED = false
OPTIONSELI_DEMO_MODE = true
```

Ask Tradier support whether an active account holder may use a personal API token in
a private Streamlit Community Cloud application accessible only by that same account
holder. Ask whether production and sandbox quote/option-chain display are both
permitted and whether Partner/OAuth status or a separate market-data license is
required. Do not enable the private-cloud flag without an affirmative written answer.

## 1. Configure Google OIDC

In Google Cloud Console:

1. Create or select a project.
2. Configure the OAuth consent screen for your own Google account.
3. Create an **OAuth 2.0 Client ID** with application type **Web application**.
4. Add this exact authorized redirect URI:
   `https://optionseli.streamlit.app/oauth2callback`
5. Copy the client ID and client secret into Streamlit server-side Secrets only.

Generate a strong cookie secret locally, for example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not save that value in the repository.

## 2. Configure Streamlit server-side Secrets

Open the app in Streamlit Community Cloud, select **Manage app → Settings → Secrets**,
and enter the following with your real private values:

```toml
OPTIONSELI_ALLOWED_EMAILS = ["YOUR_GOOGLE_EMAIL"]
OPTIONSELI_DEMO_MODE = true
OPTIONSELI_API_CALLS_PER_MINUTE = 50
OPTIONSELI_MAX_EXPIRATIONS_PER_SCAN = 4
OPTIONSELI_PUBLIC_TRADIER_AUTHORIZED = false
OPTIONSELI_PRIVATE_CLOUD_TRADIER_AUTHORIZED = false

[auth]
redirect_uri = "https://optionseli.streamlit.app/oauth2callback"
cookie_secret = "YOUR_RANDOM_COOKIE_SECRET"

[auth.google]
client_id = "YOUR_GOOGLE_OIDC_CLIENT_ID"
client_secret = "YOUR_GOOGLE_OIDC_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

Do not add a Tradier token to the cloud yet. After receiving explicit Tradier
authorization, add these server-side values without committing them:

```toml
TRADIER_API_TOKEN = "YOUR_AUTHORIZED_TOKEN"
TRADIER_BASE_URL = "https://sandbox.tradier.com/v1"
OPTIONSELI_DEMO_MODE = false
OPTIONSELI_PRIVATE_CLOUD_TRADIER_AUTHORIZED = true
```

`OPTIONSELI_PUBLIC_TRADIER_AUTHORIZED` must remain `false`.

## 3. Make the Streamlit deployment private

1. Open **Manage app → Settings → Sharing**.
2. Under **Who can view this app**, select **Only specific people can view this app**.
3. Remove every viewer except your own account. Do not invite additional viewers.
4. Save the setting and verify the URL in a private/incognito browser.
5. Sign in through Streamlit Cloud, then sign in through the OptionsELI Google button
   using the one email in `OPTIONSELI_ALLOWED_EMAILS`.

Community Cloud private sharing happens before application execution. The OptionsELI
OIDC allowlist is a second gate and is checked before `app.py` is executed.

## 4. Security and functional checks

From the project folder:

```bash
git check-ignore .env data/optionseli.db .venv .streamlit/secrets.toml
pytest -q
```

After deployment verify:

- An incognito visitor cannot reach the Streamlit app without Cloud sign-in.
- A signed-in but non-allowlisted Google identity cannot open OptionsELI.
- No market overview, scanner, API call, or cached result renders before authentication.
- The authorized identity sees the demonstration banner while Tradier permission is pending.
- Settings, credentials, journal, and SQLite data are absent from the cloud UI.
- There is no order-entry or brokerage execution functionality.

## Local application

The Mac launcher and `app.py` continue to use the ignored local `.env` and SQLite
database. Cloud authentication and Cloud secrets do not overwrite either local file.

Official references:

- [Streamlit OIDC authentication](https://docs.streamlit.io/develop/concepts/connections/authentication)
- [Streamlit `st.login`](https://docs.streamlit.io/develop/api-reference/user/st.login)
- [Streamlit private sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)
- [Tradier API FAQ](https://docs.tradier.com/brokerage-api/overview/faq)
- [Build with Tradier](https://tradier.com/build)
