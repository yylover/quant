import itertools
from pathlib import Path
import sys
from urllib.parse import quote_plus

import pandas as pd
import pymysql
import yaml
from sqlalchemy import create_engine, text

# Ensure local package root (../sharecode) is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sharecode.backtest.vectorbt_runner import run_signals_backtest
from sharecode.strategies import common as stg


CONFIG_PATH = ROOT / "sharecode" / "config.yaml"


def _grid(params: dict) -> list[dict]:
    keys = list(params.keys())
    vals = [params[k] for k in keys]
    out = []
    for combo in itertools.product(*vals):
        out.append(dict(zip(keys, combo)))
    return out


def run_one(
    ohlc_df: pd.DataFrame,
    strategy: str,
    strat_params: dict,
    *,
    init_cash: float,
    fees: float,
    slippage: float,
) -> dict:
    close, entries, exits = stg.dispatch_signals(ohlc_df, strategy, **strat_params)
    pf, stats = run_signals_backtest(close, entries, exits, init_cash=init_cash, fees=fees, slippage=slippage, freq="1D")
    return {
        "strategy": strategy,
        **strat_params,
        "start": str(pf.close.index.min().date()),
        "end": str(pf.close.index.max().date()),
        "rows": int(pf.close.shape[0]),
        "total_return_pct": float(stats.get("Total Return [%]", float("nan"))),
        "max_drawdown_pct": float(stats.get("Max Drawdown [%]", float("nan"))),
        "sharpe": float(stats.get("Sharpe Ratio", float("nan"))),
        "calmar": float(stats.get("Calmar Ratio", float("nan"))),
        "total_trades": float(stats.get("Total Trades", float("nan"))),
        "win_rate_pct": float(stats.get("Win Rate [%]", float("nan"))),
    }


def connect_db(host: str, port: int, user: str, password: str, database: str) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        autocommit=False,
    )


def build_engine(host: str, port: int, user: str, password: str, database: str):
    pwd = quote_plus(password or "")
    url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{database}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True)


def get_instrument_id(engine, symbol: str, exchange: str) -> int:
    symbol_std = f"{symbol}.{ 'SH' if exchange.upper() == 'SSE' else 'SZ' }"
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id FROM instrument WHERE symbol = :symbol"), {"symbol": symbol_std}).fetchone()
        if not row:
            raise RuntimeError(f"instrument {symbol_std} not found in database")
        return int(row[0])


def load_ohlc_df(
    engine,
    instrument_id: int,
    interval: str,
) -> pd.DataFrame:
    sql = """
    SELECT ts, open_price, high_price, low_price, close_price
    FROM bar
    WHERE instrument_id = :instrument_id AND `interval` = :interval
    ORDER BY ts
    """
    df = pd.read_sql(sql, con=engine, params={"instrument_id": instrument_id, "interval": interval})
    if df.empty:
        raise RuntimeError("no bar data loaded from database")
    df["ts"] = pd.to_datetime(df["ts"])
    out = pd.DataFrame(
        {
            "日期": df["ts"],
            "开盘": df["open_price"].astype(float),
            "最高": df["high_price"].astype(float),
            "最低": df["low_price"].astype(float),
            "收盘": df["close_price"].astype(float),
        }
    )
    return out


def main() -> None:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    db = cfg["db"]
    scan = cfg["scan"]
    grids = scan["grids"]

    engine = build_engine(
        host=db["host"],
        port=int(db["port"]),
        user=db["user"],
        password=db["password"],
        database=db["name"],
    )
    inst_id = get_instrument_id(engine, scan["symbol"], scan["exchange"])
    ohlc_df = load_ohlc_df(engine, inst_id, scan["interval"])

    results: list[dict] = []

    for params in _grid(grids.get("supertrend", {})):
        results.append(
            run_one(
                ohlc_df,
                "supertrend",
                params,
                init_cash=scan["init_cash"],
                fees=scan["fees"],
                slippage=scan["slippage"],
            )
        )

    for params in _grid(grids.get("donchian", {})):
        results.append(
            run_one(
                ohlc_df,
                "donchian",
                params,
                init_cash=scan["init_cash"],
                fees=scan["fees"],
                slippage=scan["slippage"],
            )
        )

    for params in _grid(grids.get("ma_slope", {})):
        results.append(
            run_one(
                ohlc_df,
                "ma_slope",
                params,
                init_cash=scan["init_cash"],
                fees=scan["fees"],
                slippage=scan["slippage"],
            )
        )

    for params in _grid(grids.get("timing_ma", {})):
        results.append(
            run_one(
                ohlc_df,
                "timing_ma",
                params,
                init_cash=scan["init_cash"],
                fees=scan["fees"],
                slippage=scan["slippage"],
            )
        )

    out_df = pd.DataFrame(results)
    out_dir = ROOT / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"scan_{scan['symbol']}_trend_params.csv"
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    # Print best candidates: sort by Sharpe desc then MaxDD asc
    view = out_df.sort_values(["sharpe", "max_drawdown_pct"], ascending=[False, True]).head(20)
    print("scan_ok", "saved_to", str(out_path))
    print(view[["strategy", "total_return_pct", "max_drawdown_pct", "sharpe", "calmar", "total_trades", "win_rate_pct"] + [c for c in view.columns if c in ("atr_window","multiplier","entry_n","exit_n","window","slope_window","fast","slow")]])


if __name__ == "__main__":
    main()

