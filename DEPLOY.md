# Deploy OptionsELI as a private single-user Streamlit app

Access is controlled by Streamlit Community Cloud sharing. Set the deployment to
**Only specific people can view this app** and invite only the intended personal
accounts. Streamlit authenticates an invited viewer before serving the application.

Never commit `.env`, `data/optionseli.db`, `.streamlit/secrets.toml`, credentials,
or virtual environments.

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

## 1. Configure Streamlit server-side Secrets

Open the app in Streamlit Community Cloud, select **Manage app → Settings → Secrets**,
and enter the following with your real private values:

```toml
OPTIONSELI_DEMO_MODE = true
OPTIONSELI_API_CALLS_PER_MINUTE = 50
OPTIONSELI_MAX_EXPIRATIONS_PER_SCAN = 4
OPTIONSELI_PUBLIC_TRADIER_AUTHORIZED = false
OPTIONSELI_PRIVATE_CLOUD_TRADIER_AUTHORIZED = false
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

The application does not require `[auth]`, Google OAuth client credentials, a cookie
secret, or `OPTIONSELI_ALLOWED_EMAILS`. Those obsolete values may be removed from
Cloud Secrets; OptionsELI does not read them.

## 2. Make the Streamlit deployment private

1. Open **Manage app → Settings → Sharing**.
2. Under **Who can view this app**, select **Only specific people can view this app**.
3. Keep only your intended personal email accounts in the viewer list.
4. Save the setting and verify the URL in a private/incognito browser.
5. Sign in using one of the email accounts invited through Streamlit private sharing.

Community Cloud private sharing happens before application execution. OptionsELI does
not add a second login prompt.

## 3. Security and functional checks

From the project folder:

```bash
git check-ignore .env data/optionseli.db .venv .streamlit/secrets.toml
pytest -q
```

After deployment verify:

- An incognito visitor cannot reach the Streamlit app without Cloud sign-in.
- An account that is not in the Streamlit viewer list cannot open OptionsELI.
- No dashboard content is served to an unauthenticated visitor.
- The authorized identity sees the demonstration banner while Tradier permission is pending.
- Settings, credentials, journal, and SQLite data are absent from the cloud UI.
- There is no order-entry or brokerage execution functionality.

## Local application

The Mac launcher and `app.py` continue to use the ignored local `.env` and SQLite
database. Cloud sharing and Cloud secrets do not overwrite either local file.

Official references:

- [Streamlit private sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)
- [Tradier API FAQ](https://docs.tradier.com/brokerage-api/overview/faq)
- [Build with Tradier](https://tradier.com/build)
