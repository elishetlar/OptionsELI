from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, strategy TEXT NOT NULL,
  entry_date TEXT NOT NULL, exit_date TEXT, expiration TEXT, short_strike REAL,
  long_strike REAL, contracts INTEGER NOT NULL DEFAULT 1, entry_credit REAL NOT NULL,
  exit_debit REAL, fees REAL NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT ''
)
"""


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(SCHEMA)
    connection.commit()
    return connection


def add_trade(connection: sqlite3.Connection, values: dict) -> None:
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(f"INSERT INTO trades ({columns}) VALUES ({placeholders})", tuple(values.values()))
    connection.commit()


def load_trades(connection: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM trades ORDER BY entry_date DESC, id DESC", connection)


def journal_metrics(trades: pd.DataFrame) -> dict[str, float]:
    if trades.empty or "exit_debit" not in trades or trades["exit_debit"].notna().sum() == 0:
        return {"Realized P/L": 0.0, "Win rate": 0.0, "Average return": 0.0, "Maximum drawdown": 0.0}
    closed = trades.dropna(subset=["exit_debit"]).copy()
    closed["pnl"] = (closed["entry_credit"] - closed["exit_debit"]) * 100 * closed["contracts"] - closed["fees"]
    closed["return"] = closed["pnl"] / (closed["entry_credit"] * 100 * closed["contracts"]).replace(0, pd.NA)
    equity = closed.sort_values("exit_date")["pnl"].cumsum()
    drawdown = equity - equity.cummax().clip(lower=0)
    return {"Realized P/L": float(closed["pnl"].sum()), "Win rate": float((closed["pnl"] > 0).mean() * 100), "Average return": float(closed["return"].mean() * 100), "Maximum drawdown": float(drawdown.min())}
