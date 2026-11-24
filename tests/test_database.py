import sqlite3

from optionseli.database import add_trade, journal_metrics, load_trades


def test_journal_metrics():
    db = sqlite3.connect(":memory:")
    from optionseli.database import SCHEMA
    db.execute(SCHEMA)
    add_trade(db, {"symbol":"SPY", "strategy":"put_credit", "entry_date":"2025-01-01", "exit_date":"2025-01-10", "contracts":1, "entry_credit":1.0, "exit_debit":.4, "fees":2.0})
    metrics = journal_metrics(load_trades(db))
    assert metrics["Realized P/L"] == 58
    assert metrics["Win rate"] == 100
