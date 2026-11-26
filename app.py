from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from optionseli.backtest import underlying_signal_test
from optionseli.config import DEFAULTS, LIQUID_UNIVERSE, get_settings
from optionseli.database import add_trade, connect, journal_metrics, load_trades
from optionseli.demo_data import demo_option_chain, demo_prices
from optionseli.diagnostics import log_event, log_failure
from optionseli.indicators import calculate_indicators, latest_snapshot
from optionseli.market_data import yahoo_history
from optionseli.rate_limit import RateLimitExceeded, SlidingWindowRateLimiter
from optionseli.signals import assess_market_regime, assess_trend, choose_strategy
from optionseli.strategy_scoring import score_candidate_with_context
from optionseli.settings_store import masked_token_hint, save_market_settings
from optionseli.spreads import build_credit_spreads, payoff_at_expiration
from optionseli.tradier import TradierClient, TradierError, chain_data_is_stale
from optionseli.ui_policy import available_pages, options_scan_available

st.set_page_config(page_title="OptionsELI", page_icon="📈", layout="wide")
st.markdown("""
<style>
:root { color-scheme: dark; --accent:#00c896; --panel:#101722; --border:#263244; --muted:#98a6b8; }
html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"] { color:#f2f5f8 !important; }
.stApp, [data-testid="stAppViewContainer"] { background:radial-gradient(circle at 82% -8%, #152a3f 0, #080d16 34%, #070b12 72%) fixed !important; }
[data-testid="stHeader"] { background:rgba(7,11,18,.82) !important; backdrop-filter:blur(16px); }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#0d1521 0%,#090e17 100%) !important; border-right:1px solid var(--border); }
[data-testid="stSidebar"] * { color:#e9eef5 !important; }
h1,h2,h3,h4,h5,h6,p,label,span,div { color:inherit; }
h1 { letter-spacing:-.035em; font-weight:750 !important; }
h2,h3 { letter-spacing:-.02em; }
[data-testid="stMetric"] { background:linear-gradient(145deg,#121c2b,#0d1520); border:1px solid var(--border); padding:16px; border-radius:12px; box-shadow:0 10px 28px rgba(0,0,0,.22); }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { color:#9eacbd !important; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { color:#f7fafc !important; font-weight:700 !important; }
[data-testid="stMetricDelta"] * { color:#00d39f !important; }
.stButton>button, .stDownloadButton>button { background:#00c896 !important; color:#04110d !important; border:0 !important; border-radius:8px !important; font-weight:700 !important; }
.stButton>button:hover { background:#20ddb0 !important; box-shadow:0 0 0 3px rgba(0,200,150,.18); }
input, textarea, [data-baseweb="input"], [data-baseweb="select"]>div, [data-baseweb="textarea"] { background:#0d1520 !important; color:#f2f5f8 !important; border-color:#2a384c !important; }
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"], [role="option"] { background:#111a27 !important; color:#f2f5f8 !important; }
[role="option"]:hover, [aria-selected="true"] { background:#1c3242 !important; }
[data-testid="stDataFrame"], [data-testid="stTable"] { background:#0d1520 !important; border:1px solid var(--border); border-radius:10px; overflow:hidden; }
[data-testid="stAlert"] { color:#f2f5f8 !important; border-radius:9px; }
.demo-banner { padding:12px 16px; border:1px solid #e6a23c; background:#35270c; color:#ffd88a !important; border-radius:9px; font-weight:700; }
.source { color:#9eacbd !important; font-size:.82rem; margin:.3rem 0 .8rem; }
.status-row { display:flex; gap:8px; align-items:center; margin:.25rem 0 1rem; flex-wrap:wrap; }
.status-badge { display:inline-flex; align-items:center; gap:7px; border-radius:999px; padding:6px 11px; font-size:.78rem; font-weight:750; letter-spacing:.03em; border:1px solid; }
.status-badge:before { content:''; width:7px; height:7px; border-radius:50%; background:currentColor; box-shadow:0 0 8px currentColor; }
.status-demo { color:#ffca67 !important; background:#30250e; border-color:#775b20; }
.status-delayed { color:#ff9d66 !important; background:#321b12; border-color:#70402b; }
.status-live { color:#38dfa9 !important; background:#0c2b23; border-color:#226451; }
.status-offline { color:#ff6f7d !important; background:#32151a; border-color:#71313a; }
.feature-card { background:#0d1520; border:1px solid var(--border); border-radius:10px; padding:12px 14px; color:#cbd4df !important; }
hr { border-color:#253246 !important; }
@media (max-width: 768px) {
  .block-container { padding:1rem .8rem 4rem !important; }
  h1 { font-size:1.8rem !important; }
  h2 { font-size:1.35rem !important; }
  [data-testid="stMetric"] { padding:11px; }
  .status-row { align-items:flex-start; }
  .status-badge { font-size:.7rem; }
  [data-testid="stDataFrame"] { font-size:.78rem; }
}
</style>
""", unsafe_allow_html=True)

try:
    cloud_secrets = dict(st.secrets)
except (FileNotFoundError, RuntimeError):
    cloud_secrets = {}
settings = get_settings(secret_values=cloud_secrets)
db = None if settings.public_mode else connect(settings.db_path)


def data_badge(label: str, kind: str, detail: str = "") -> None:
    st.markdown(f"<div class='status-row'><span class='status-badge status-{kind}'>{label}</span><span class='source'>{detail}</span></div>", unsafe_allow_html=True)


def source_line(meta) -> None:
    if meta.is_synthetic:
        state, kind = "DEMONSTRATION DATA", "demo"
    elif meta.is_delayed:
        state, kind = "DELAYED DATA", "delayed"
    else:
        state, kind = "PROVIDER DATA · VERIFY TIMESTAMP", "live"
    observed = f" · Latest observation: {meta.observed_at}" if getattr(meta, "observed_at", "") else ""
    note = f"Source: {meta.source} · Retrieved: {meta.retrieved_at}{observed} · {meta.note}"
    data_badge(state, kind, note)


@st.cache_data(ttl=900, show_spinner=False)
def get_prices(symbol: str, demo: bool):
    if demo:
        return demo_prices(symbol)
    if settings.tradier_token:
        end = date.today()
        start = end - timedelta(days=430)
        get_api_limiter(settings.api_calls_per_minute).acquire()
        return TradierClient(settings.tradier_token, settings.tradier_base_url).history(symbol, start, end)
    if settings.public_mode:
        raise TradierError("Hosted Tradier credentials are unavailable; live market data is disabled")
    return yahoo_history(symbol)


@st.cache_data(ttl=60, show_spinner=False)
def get_tradier_quote(symbol: str):
    get_api_limiter(settings.api_calls_per_minute).acquire()
    return TradierClient(settings.tradier_token, settings.tradier_base_url).quote(symbol)


@st.cache_resource
def get_api_limiter(limit: int) -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(limit, 60)


@st.cache_data(ttl=900, show_spinner=False)
def get_tradier_expirations(symbol: str):
    get_api_limiter(settings.api_calls_per_minute).acquire()
    return TradierClient(settings.tradier_token, settings.tradier_base_url).expirations(symbol)


@st.cache_data(ttl=300, show_spinner=False)
def get_tradier_chain(symbol: str, expiration_iso: str):
    get_api_limiter(settings.api_calls_per_minute).acquire()
    client = TradierClient(settings.tradier_token, settings.tradier_base_url)
    chain, meta = client.option_chain(symbol, date.fromisoformat(expiration_iso))
    meta = type(meta)(
        meta.source, meta.retrieved_at, meta.is_synthetic, meta.is_delayed,
        f"{meta.note} Cached for up to 5 minutes.", meta.observed_at,
    )
    return chain, meta


def chart_prices(df: pd.DataFrame, symbol: str):
    enriched = calculate_indicators(df)
    fig = go.Figure(go.Candlestick(x=enriched.index, open=enriched.Open, high=enriched.High, low=enriched.Low, close=enriched.Close, name=symbol))
    for col, color in (("SMA_20", "#43d9ad"), ("SMA_50", "#4f8cff"), ("SMA_200", "#ffb547")):
        fig.add_trace(go.Scatter(x=enriched.index, y=enriched[col], name=col.replace("_", " "), line={"width": 1.4, "color": color}))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b111b", plot_bgcolor="#0b111b", font={"color":"#dfe7f1"}, height=470, margin=dict(l=10, r=10, t=35, b=10), xaxis_rangeslider_visible=False, xaxis={"gridcolor":"#202b3a"}, yaxis={"gridcolor":"#202b3a"})
    return fig


def analyze_credit_spread_symbol(
    symbol, demo, dte, directions, delta_range, target_credit, credit_tolerance,
    loss_range, widths, max_ba, min_oi, fees, min_ror, market_regime,
):
    """Fetch and rank one symbol without substituting demo data after a live failure."""
    price_df, price_meta = get_prices(symbol, demo)
    if demo:
        spot = float(price_df.Close.iloc[-1])
        chain, chain_meta = demo_option_chain(symbol, spot)
    else:
        quote = get_tradier_quote(symbol)
        if quote.get("latest") is None:
            raise TradierError(f"Tradier returned no usable current price for {symbol}")
        spot = float(quote["latest"])
        expirations = get_tradier_expirations(symbol)
        eligible = [x for x in expirations if dte[0] <= (x - date.today()).days <= dte[1]][:settings.max_expirations_per_scan]
        frames, metas = [], []
        for expiration in eligible:
            frame, meta = get_tradier_chain(symbol, expiration.isoformat())
            frames.append(frame); metas.append(meta)
        chain = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        chain_meta = metas[-1] if metas else None
        if chain.empty:
            raise TradierError(f"No Tradier option chains were available for {symbol} in the selected DTE range")
        if chain_data_is_stale(chain):
            raise TradierError(f"{symbol} option quotes are stale or lack verifiable timestamps; No Trade")

    snapshot = latest_snapshot(price_df)
    signal = assess_trend(price_df, price_meta)
    decision = choose_strategy(signal, market_regime)
    rankings = {}
    for key in directions:
        candidates = build_credit_spreads(
            chain, symbol, key, delta_range[0], delta_range[1], target_credit,
            credit_tolerance, loss_range[0], loss_range[1], tuple(widths),
            max_ba, int(min_oi), fees,
        )
        scored = (score_candidate_with_context(c, snapshot, signal, market_regime) for c in candidates)
        rankings[key] = [] if (signal.stale or market_regime.stale) else sorted(
            (c for c in scored if c.return_on_risk >= min_ror), key=lambda x: x.score, reverse=True
        )
    return {
        "symbol": symbol, "spot": spot, "price_meta": price_meta, "chain_meta": chain_meta,
        "chain": chain, "signal": signal, "decision": decision, "rankings": rankings,
    }


st.sidebar.title("OptionsELI")
st.sidebar.caption("Market & options research")
pages = available_pages(settings.public_mode)
page = st.sidebar.radio("Workspace", pages)
hosted_tradier_allowed = settings.public_tradier_authorized or (
    settings.private_cloud_mode and settings.private_cloud_tradier_authorized
)
public_demo_required = settings.public_mode and not hosted_tradier_allowed
demo = st.sidebar.toggle(
    "Demonstration mode",
    value=True if public_demo_required else settings.demo_mode,
    disabled=public_demo_required,
    help="Required in the public edition until Tradier grants Partner/data-redistribution authorization." if public_demo_required else "Uses clearly labeled synthetic prices and option chains.",
)
log_event("page_render", page=page, public_mode=settings.public_mode, demo_mode=demo)
if demo:
    st.markdown("<div class='demo-banner'>DEMONSTRATION MODE — all displayed prices and option contracts are synthetic and must not be used for trading.</div>", unsafe_allow_html=True)
st.sidebar.warning("Research only. Options involve substantial risk. No order execution is included.")
if settings.public_mode:
    st.sidebar.caption("Hosted read-only edition · No journal, credential controls, or order routing")

if demo:
    data_badge("DEMONSTRATION", "demo", "Synthetic prices and chains; no market connection is being used.")
elif settings.public_mode and not hosted_tradier_allowed:
    data_badge("CLOUD TRADIER DATA DISABLED", "offline", "Cloud use of the personal Tradier token is awaiting explicit Tradier authorization. Demonstration mode remains available.")
elif not settings.tradier_token:
    data_badge("MARKET DATA NOT CONFIGURED", "offline", "Tradier token missing. Stock pages may use delayed Yahoo data; options scanning is unavailable.")
elif "sandbox" in settings.tradier_base_url:
    data_badge("TRADIER SANDBOX · DELAYED", "delayed", "Read-only sandbox connection. Option quotes may be delayed.")
else:
    data_badge("TRADIER PRODUCTION", "live", "Real-time status depends on your Tradier market-data entitlement; verify timestamps before use.")

if page == "Market Overview":
    st.title("Market Overview")
    st.caption("Broad-market trend and volatility monitor. Economic events are not fabricated; calendar integration is planned for Phase 2.")
    cards = st.columns(4)
    datasets = {}
    for column, symbol in zip(cards, ["SPY", "QQQ", "IWM", "VIX"]):
        try:
            df, meta = get_prices(symbol, demo)
            datasets[symbol] = (df, meta)
            snap = latest_snapshot(df)
            if not demo and settings.tradier_token:
                quote = get_tradier_quote(symbol)
                current_price = float(quote["latest"]) if quote.get("latest") is not None else float(snap["Price"])
                change_pct = quote.get("change_percentage")
                if change_pct is None and quote.get("prevclose"):
                    change_pct = (current_price / float(quote["prevclose"]) - 1) * 100
            else:
                current_price = float(snap["Price"])
                previous = float(df.Close.iloc[-2])
                change_pct = (current_price / previous - 1) * 100
            column.metric(symbol, f"{current_price:.2f}", f"{float(change_pct):.2f}%" if change_pct is not None else "Unavailable")
            column.caption(f"{snap['Trend']} · RSI {snap['RSI']:.1f}")
        except Exception as exc:
            log_failure("market_overview_symbol_failed", exc, symbol=symbol)
            column.error(f"{symbol}: {exc}")
    selected = st.selectbox("Chart", list(datasets), index=0) if datasets else None
    if selected:
        st.plotly_chart(chart_prices(datasets[selected][0], selected), width="stretch")
        source_line(datasets[selected][1])
        selected_snapshot = latest_snapshot(datasets[selected][0])
        indicator_columns = st.columns(5)
        indicator_columns[0].metric("RSI (14)", f"{selected_snapshot['RSI']:.1f}")
        indicator_columns[1].metric("MACD", f"{selected_snapshot['MACD']:.2f}")
        indicator_columns[2].metric("ATR (14)", f"{selected_snapshot['ATR']:.2f}")
        indicator_columns[3].metric("Support", f"${selected_snapshot['Support']:.2f}")
        indicator_columns[4].metric("Resistance", f"${selected_snapshot['Resistance']:.2f}")
        if all(item in datasets for item in ("SPY", "QQQ", "VIX")):
            spy_signal = assess_trend(*datasets["SPY"])
            qqq_signal = assess_trend(*datasets["QQQ"])
            regime = assess_market_regime(spy_signal, qqq_signal, *datasets["VIX"])
            st.subheader(f"Market regime: {regime.classification}")
            st.write(list(regime.explanations))
    else:
        st.warning("Market history is temporarily unavailable. Try again later or use Demonstration mode.")
    st.subheader("Economic events")
    st.info("No verified economic-calendar provider is configured. OptionsELI intentionally displays no events rather than inventing dates. Add an approved calendar source in Phase 2.")

elif page == "Stock Scanner":
    st.title("Stock Scanner")
    selected = st.multiselect(
        "Universe (50 liquid stocks and ETFs)", LIQUID_UNIVERSE,
        default=LIQUID_UNIVERSE[:10], max_selections=20 if settings.public_mode else None,
        help="Public scans are limited to 20 symbols per run to protect shared data services." if settings.public_mode else None,
    )
    trend_filter = st.selectbox("Trend filter", ["All", "Bullish", "Mixed", "Bearish"])
    if st.button("Run stock scan", type="primary"):
        rows, last_meta, failures = [], None, []
        progress = st.progress(0)
        for i, symbol in enumerate(selected):
            try:
                df, last_meta = get_prices(symbol, demo)
                row = {"Symbol": symbol, **latest_snapshot(df)}
                if not demo and settings.tradier_token:
                    quote = get_tradier_quote(symbol)
                    if quote.get("latest") is not None:
                        row["Price"] = float(quote["latest"])
                    row["Daily change %"] = quote.get("change_percentage")
                rows.append(row)
            except Exception as exc:
                log_failure("stock_scan_symbol_failed", exc, symbol=symbol)
                failures.append(f"{symbol}: {exc}")
            progress.progress((i + 1) / max(1, len(selected)))
        result = pd.DataFrame(rows)
        if trend_filter != "All" and not result.empty:
            result = result[result.Trend == trend_filter]
        st.dataframe(result, width="stretch", hide_index=True, column_config={"Price": st.column_config.NumberColumn(format="$%.2f"), "RSI": st.column_config.NumberColumn(format="%.1f")})
        if last_meta: source_line(last_meta)
        if failures: st.warning("Some symbols failed: " + " | ".join(failures))

elif page == "Options Scanner":
    st.title("Options Credit Spread Scanner")
    st.caption("Automatic mode evaluates both directions, market regime, technical placement, liquidity and risk/reward. A scan may correctly return No Trade.")
    public_tradier_allowed = not settings.public_mode or hosted_tradier_allowed
    scan_available = options_scan_available(demo, bool(settings.tradier_token), public_tradier_allowed)
    if not scan_available:
        if settings.public_mode and not hosted_tradier_allowed:
            st.error("Live Tradier options data is unavailable in the hosted edition pending explicit Tradier authorization. Turn on Demonstration mode to use the scanner with clearly labeled synthetic data.")
        else:
            st.error("Options scanning is unavailable because the server-side market-data connection is not configured. Demonstration mode remains available.")
    c1, c2, c3 = st.columns(3)
    if settings.public_mode:
        symbols = c1.multiselect("Underlyings (up to 5)", LIQUID_UNIVERSE, default=["SPY"], max_selections=5)
    else:
        raw_symbols = c1.text_input("Underlyings (comma separated)", "SPY")
        symbols = list(dict.fromkeys(item.strip().upper() for item in raw_symbols.split(",") if item.strip()))[:5]
    strategy = c2.selectbox("Strategy", ["Automatic — evaluate both", "Put credit spread", "Call credit spread"])
    dte = c3.slider("Days to expiration", 1, 90, (DEFAULTS["dte_min"], DEFAULTS["dte_max"]))
    c1, c2, c3, c4 = st.columns(4)
    delta_range = c1.slider("Absolute short delta", 0.01, 0.50, (DEFAULTS["delta_min"], DEFAULTS["delta_max"]), .01)
    target_credit = c2.number_input("Target credit per share", .05, 10.0, DEFAULTS["target_credit"], .05)
    credit_tolerance = c3.number_input("Credit tolerance ±", .05, 5.0, .75, .05)
    width = c4.multiselect("Spread width", [1.0, 2.0, 2.5, 5.0, 10.0], default=DEFAULTS["widths"])
    c1, c2, c3, c4 = st.columns(4)
    loss_range = c1.slider("Maximum loss ($)", 0, 2000, (int(DEFAULTS["max_loss_min"]), int(DEFAULTS["max_loss_max"])), 25)
    max_ba = c2.number_input("Max leg bid-ask", .01, 5.0, DEFAULTS["max_bid_ask"], .05)
    min_oi = c3.number_input("Minimum leg open interest", 0, 100000, DEFAULTS["min_open_interest"], 25)
    fees = c4.number_input("Round-trip costs / spread", 0.0, 50.0, DEFAULTS["transaction_cost"], .10)
    min_ror = st.slider("Minimum return on risk (%)", 0.0, 50.0, 5.0, 0.5)
    st.info("Earnings and major economic events: unavailable — no verified event provider is configured. Event dates are not inferred and are not used in ranking.")
    if st.button("Scan option chains", type="primary", disabled=not scan_available):
        if not symbols:
            st.error("Select at least one underlying.")
        elif not width:
            st.error("Select at least one spread width.")
        else:
            try:
                regime_data = {item: get_prices(item, demo) for item in ("SPY", "QQQ", "VIX")}
                spy_signal = assess_trend(*regime_data["SPY"])
                qqq_signal = assess_trend(*regime_data["QQQ"])
                market_regime = assess_market_regime(
                    spy_signal, qqq_signal, regime_data["VIX"][0], regime_data["VIX"][1]
                )
                directions = ["put_credit", "call_credit"] if strategy.startswith("Automatic") else (["put_credit"] if strategy.startswith("Put") else ["call_credit"])
                all_ranked, failures = [], []
                for symbol in symbols:
                    try:
                        result = analyze_credit_spread_symbol(
                            symbol, demo, dte, directions, delta_range, target_credit,
                            credit_tolerance, loss_range, width, max_ba, min_oi, fees,
                            min_ror, market_regime,
                        )
                    except (RateLimitExceeded, TradierError, RuntimeError, ValueError) as exc:
                        log_failure("options_scan_symbol_failed", exc, symbol=symbol)
                        failures.append(f"{symbol}: {exc}")
                        continue
                    signal, decision, rankings = result["signal"], result["decision"], result["rankings"]
                    st.header(f"{symbol} · ${result['spot']:.2f}")
                    signal_cols = st.columns(4)
                    signal_cols[0].metric("Trend", signal.classification)
                    signal_cols[1].metric("Bullish", f"{signal.bullish_score:.1f}/100")
                    signal_cols[2].metric("Bearish", f"{signal.bearish_score:.1f}/100")
                    signal_cols[3].metric("Market regime", market_regime.classification)
                    if strategy.startswith("Automatic"):
                        if decision.preferred_strategy is None:
                            st.error("NO TRADE — " + " ".join(decision.reasons))
                        elif not rankings.get(decision.preferred_strategy):
                            st.error(f"NO TRADE — {decision.classification} was preferred, but no spread passed all filters.")
                        else:
                            st.success(f"Automatic selection: {decision.classification}. " + " ".join(decision.reasons))
                    with st.expander(f"{symbol} signal evidence"):
                        st.write(list(signal.components)); st.write("Market regime", list(market_regime.explanations))
                        if signal.unavailable: st.write("Unavailable inputs", list(signal.unavailable))
                    for key, heading in (("put_credit", "Put credit spreads"), ("call_credit", "Call credit spreads")):
                        if key not in rankings: continue
                        ranked = rankings[key]
                        st.subheader(heading)
                        if not ranked:
                            st.info("No qualifying spreads in this direction."); continue
                        all_ranked.extend(ranked)
                        st.dataframe(pd.DataFrame([{
                            "Symbol": c.symbol, "Score": c.score, "Expiration": c.expiration,
                            "Short": c.short_strike, "Long": c.long_strike,
                            "Mid credit": c.midpoint_credit, "Conservative credit": c.conservative_credit,
                            "Max profit after costs": c.max_profit, "Max loss after costs": c.max_loss,
                            "Breakeven": c.breakeven, "Reward/risk": round(c.max_profit / c.max_loss, 3),
                            "Return on risk %": c.return_on_risk, "Combined bid-ask": c.bid_ask_width,
                            "|Delta|": abs(c.short_delta or 0), "Delta-based OTM estimate %": c.estimated_otm_probability,
                            "OI": c.open_interest, "Transaction costs": c.transaction_cost,
                            f"Distance beyond {c.technical_level}": c.technical_distance,
                            "Distance (ATR)": c.technical_distance_atr,
                        } for c in ranked]), width="stretch", hide_index=True)
                        for index, candidate in enumerate(ranked[:3]):
                            with st.expander(f"#{index + 1}: {candidate.expiration} · {candidate.short_strike}/{candidate.long_strike} · score {candidate.score}"):
                                st.write("Why selected", list(candidate.reasons)); st.write("Main risks", list(candidate.risks))
                                st.write("Invalidation", candidate.invalidation); st.write("Score components", candidate.score_details)
                                st.caption("The OTM estimate is 1 − absolute Tradier delta. It is a rough model-based approximation, not a probability guarantee.")
                    source_line(result["price_meta"])
                    if result["chain_meta"]: source_line(result["chain_meta"])
                    if result["chain"].get("delta", pd.Series(dtype=float)).isna().any():
                        st.warning("Contracts with missing Tradier Greeks were excluded; no estimates were substituted.")
                if failures: st.warning("Unavailable symbols: " + " | ".join(failures))
                if all_ranked:
                    labels = [f"{c.symbol} · {c.strategy} · {c.expiration} · {c.short_strike}/{c.long_strike} · {c.score}" for c in all_ranked]
                    chosen = all_ranked[labels.index(st.selectbox("Expiration payoff chart", labels))]
                    prices = np.linspace(chosen.long_strike - chosen.width, chosen.short_strike + chosen.width, 180)
                    fig = go.Figure(go.Scatter(x=prices, y=payoff_at_expiration(chosen, prices), fill="tozeroy", line={"color": "#43d9ad"}))
                    fig.add_vline(x=chosen.breakeven, line_dash="dash", annotation_text="Breakeven")
                    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b111b", plot_bgcolor="#0b111b", xaxis_title="Underlying at expiration", yaxis_title="P/L per spread ($, before transaction costs)", height=390)
                    st.plotly_chart(fig, width="stretch")
                elif not failures:
                    st.info("NO TRADE — no candidate met all configured criteria.")
                st.warning("Scores and delta-based OTM estimates are heuristics, not calibrated probabilities, expected returns, or recommendations.")
            except (RateLimitExceeded, TradierError, RuntimeError, ValueError) as exc:
                log_failure("options_scan_failed", exc)
                st.error(str(exc))
            except Exception as exc:
                log_failure("options_scan_unexpected_failure", exc)
                st.error("The options scan could not be completed. No order was sent. Please try again later.")

elif page == "Trade Journal" and not settings.public_mode:
    st.title("Trade Journal")
    with st.form("journal"):
        cols = st.columns(4)
        values = {"symbol": cols[0].text_input("Symbol", "SPY").upper(), "strategy": cols[1].selectbox("Strategy", ["put_credit", "call_credit", "long_call", "long_put"]), "entry_date": cols[2].date_input("Entry date", date.today()).isoformat(), "expiration": cols[3].date_input("Expiration", date.today() + timedelta(days=30)).isoformat()}
        cols = st.columns(4)
        values.update({"short_strike": cols[0].number_input("Short strike", 0.0), "long_strike": cols[1].number_input("Long strike", 0.0), "contracts": cols[2].number_input("Contracts", 1, 100, 1), "entry_credit": cols[3].number_input("Entry credit/debit", -100.0, 100.0, 1.0, .05)})
        cols = st.columns(4)
        closed = cols[0].checkbox("Closed")
        exit_date = cols[1].date_input("Exit date", date.today(), disabled=not closed)
        exit_debit = cols[2].number_input("Exit debit/credit", -100.0, 100.0, 0.0, .05, disabled=not closed)
        values.update({"fees": cols[3].number_input("Total fees", 0.0, 1000.0, 2.60, .10), "notes": st.text_area("Notes"), "exit_date": exit_date.isoformat() if closed else None, "exit_debit": exit_debit if closed else None})
        if st.form_submit_button("Save trade", type="primary"):
            add_trade(db, values); st.success("Trade saved locally.")
    trades = load_trades(db)
    metrics = journal_metrics(trades)
    cols = st.columns(4)
    cols[0].metric("Realized P/L", f"${metrics['Realized P/L']:,.2f}")
    cols[1].metric("Win rate", f"{metrics['Win rate']:.1f}%")
    cols[2].metric("Average return", f"{metrics['Average return']:.1f}%")
    cols[3].metric("Max drawdown", f"${metrics['Maximum drawdown']:,.2f}")
    st.dataframe(trades, width="stretch", hide_index=True)

elif page == "Testing Lab":
    st.title("Paper Trading & Historical Testing Lab")
    st.warning("This v1 lab tests lagged underlying-price signals only. It does not fabricate historical option chains and cannot claim historical spread performance.")
    symbol = st.selectbox("Underlying", LIQUID_UNIVERSE)
    holding = st.slider("Forward holding period (trading days)", 1, 30, 10)
    costs = st.number_input("Underlying-model transaction cost (basis points)", 0.0, 100.0, 5.0)
    if st.button("Run signal test", type="primary"):
        try:
            df, meta = get_prices(symbol, demo)
            result = underlying_signal_test(df, holding, costs)
            if result.empty:
                st.info("Not enough history for this test.")
            else:
                active = result.loc[result.signal == 1, "test_return"]
                average = active.mean() if not active.empty else float("nan")
                st.metric("Average conditional forward return", f"{average*100:.2f}%" if pd.notna(average) else "Unavailable")
                curve = (1 + result.test_return.fillna(0)).cumprod()
                st.line_chart(curve)
                st.caption("Signals are shifted one bar to avoid look-ahead bias; future returns are used only as outcomes. This is not an options backtest.")
            source_line(meta)
        except Exception as exc:
            log_failure("testing_lab_failed", exc, symbol=symbol)
            st.error("Historical price data is temporarily unavailable. Try again later or use Demonstration mode.")

elif page == "Settings" and not settings.public_mode:
    st.title("Settings")
    st.caption("Configure local data access. Secrets are saved only to the ignored `.env` file with owner-only permissions and are never displayed in full.")
    st.subheader("Tradier market data")
    if settings.tradier_token:
        st.success(masked_token_hint(settings.tradier_token))
    else:
        st.warning("Tradier is not configured. Live options chains and expiration discovery are unavailable.")
    environment = st.selectbox(
        "Tradier environment",
        ["Sandbox (recommended for setup)", "Production"],
        index=0 if "sandbox" in settings.tradier_base_url else 1,
        help="Sandbox data is delayed. Production data timing depends on your Tradier subscription and exchange entitlements.",
    )
    token_input = st.text_input("API token", type="password", placeholder="Leave blank to keep the saved token")
    account_input = st.text_input("Account ID (optional for market data)", value=settings.tradier_account_id, type="password")
    default_demo = st.checkbox("Start in demonstration mode", value=settings.demo_mode)
    base_url = "https://sandbox.tradier.com/v1" if environment.startswith("Sandbox") else "https://api.tradier.com/v1"
    test_token = token_input.strip() or settings.tradier_token
    left, right = st.columns(2)
    if left.button("Test connection", type="primary", width="stretch"):
        if not test_token:
            st.error("Enter a Tradier token before testing.")
        else:
            try:
                result = TradierClient(test_token, base_url).test_connection()
                st.success(f"Authenticated successfully. Market state: {result['state']}. {result['description']}")
                if "sandbox" in base_url:
                    st.warning("Connection is valid, but sandbox market data is delayed.")
                else:
                    st.info("Production connection is valid. Real-time access still depends on your Tradier data entitlement.")
            except TradierError as exc:
                st.error(f"Connection test failed: {exc}")
    if right.button("Save settings", width="stretch"):
        final_token = token_input.strip() or settings.tradier_token
        save_market_settings(final_token, account_input.strip(), base_url, default_demo)
        st.cache_data.clear()
        st.success("Settings saved securely. Reloading OptionsELI…")
        st.rerun()
    st.subheader("Feature availability")
    availability = pd.DataFrame([
        {"Feature":"Demonstration dashboard", "Status":"Available", "Requirement":"None"},
        {"Feature":"Stock and ETF history", "Status":"Available, generally delayed" if not demo else "Synthetic demo data", "Requirement":"Internet access outside demo mode"},
        {"Feature":"Options chains and spreads", "Status":"Available" if (demo or settings.tradier_token) else "Unavailable", "Requirement":"Tradier token or demonstration mode"},
        {"Feature":"Tradier real-time quotes", "Status":"Entitlement dependent" if settings.tradier_token and "sandbox" not in settings.tradier_base_url else "Unavailable", "Requirement":"Production token plus Tradier real-time entitlement"},
        {"Feature":"Verified earnings calendar", "Status":"Unavailable", "Requirement":"Phase 2 calendar provider"},
        {"Feature":"Verified economic calendar", "Status":"Unavailable", "Requirement":"Phase 2 calendar provider"},
        {"Feature":"Historical options backtest", "Status":"Unavailable", "Requirement":"Real archived historical option chains"},
        {"Feature":"Journal and underlying signal lab", "Status":"Available", "Requirement":"None"},
    ])
    st.dataframe(availability, width="stretch", hide_index=True)

else:
    st.error("This private local feature is unavailable in the public read-only edition.")

st.divider()
st.caption("OptionsELI v0.1 · Research only · Risks include early assignment, expiration/pin risk, liquidity changes, data errors, and correlated positions.")
