import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "sharecode" / "config.yaml"


def run(cmd: list[str]) -> None:
    print(">>", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    db = cfg["db"]
    data = cfg["data"]
    strat_single = cfg["strategy"]["single"]
    strat_port = cfg["strategy"]["portfolio"]

    # 1. 拉取并导入所有 ETF 日线数据
    for etf in data["etfs"]:
        symbol = etf["symbol"]
        market = etf["market"]
        name = etf["name"]
        exchange = etf["exchange"]
        etf_type = etf.get("type", "etf")

        # 1.1 用 AkShare 拉取 CSV
        run(
            [
                "python",
                "sharecode/scripts/akshare_fetch_cache.py",
                "--symbol",
                symbol,
                "--start",
                data["start"],
                "--end",
                data["end"],
                "--adjust",
                data["adjust"],
                "--sec-type",
                "etf",
                "--market",
                market,
            ]
        )

        # 1.2 将 CSV 导入 MySQL
        csv_path = ROOT / "data" / f"{symbol}_daily_{data['adjust']}.csv"
        run(
            [
                "python",
                "sharecode/scripts/load_csv_to_mysql.py",
                "--csv",
                str(csv_path),
                "--symbol",
                symbol,
                "--exchange",
                exchange,
                "--name",
                name,
                "--type",
                etf_type,
                "--interval",
                "1d",
                "--db-host",
                str(db["host"]),
                "--db-port",
                str(db["port"]),
                "--db-user",
                db["user"],
                "--db-password",
                db["password"],
                "--db-name",
                db["name"],
            ]
        )

        # 1.3 单标趋势回测（数据库行情）
        backtest_cmd = [
            "python",
            "sharecode/scripts/backtest_from_mysql.py",
            "--symbol",
            symbol,
            "--exchange",
            exchange,
            "--interval",
            "1d",
            "--strategy",
            strat_single["strategy"],
            "--init-cash",
            str(strat_single["init_cash"]),
            "--fees",
            str(strat_single["fees"]),
            "--slippage",
            str(strat_single["slippage"]),
            "--sl-pct",
            str(strat_single["sl_pct"]),
            "--tp-pct",
            str(strat_single["tp_pct"]),
            "--db-host",
            str(db["host"]),
            "--db-port",
            str(db["port"]),
            "--db-user",
            db["user"],
            "--db-password",
            db["password"],
            "--db-name",
            db["name"],
        ]

        # strategy-specific parameters
        if strat_single["strategy"] in ("ma_cross", "timing_ma"):
            backtest_cmd += ["--fast", str(strat_single.get("fast", 10)), "--slow", str(strat_single.get("slow", 60))]
        elif strat_single["strategy"] in ("boll_breakout", "boll_reversion"):
            backtest_cmd += ["--window", str(strat_single.get("window", 20)), "--n-std", str(strat_single.get("n_std", 2.0))]
        elif strat_single["strategy"] == "rsi_reversion":
            backtest_cmd += [
                "--rsi-window",
                str(strat_single.get("rsi_window", 14)),
                "--rsi-low",
                str(strat_single.get("rsi_low", 30.0)),
                "--rsi-high",
                str(strat_single.get("rsi_high", 70.0)),
            ]
        elif strat_single["strategy"] == "macd":
            backtest_cmd += [
                "--macd-fast",
                str(strat_single.get("macd_fast", 12)),
                "--macd-slow",
                str(strat_single.get("macd_slow", 26)),
                "--macd-signal",
                str(strat_single.get("macd_signal", 9)),
            ]
        elif strat_single["strategy"] == "donchian":
            backtest_cmd += ["--entry-n", str(strat_single.get("entry_n", 20)), "--exit-n", str(strat_single.get("exit_n", 10))]
        elif strat_single["strategy"] == "momentum":
            backtest_cmd += [
                "--lookback",
                str(strat_single.get("lookback", 60)),
                "--enter-th",
                str(strat_single.get("enter_th", 0.0)),
                "--exit-th",
                str(strat_single.get("exit_th", 0.0)),
            ]
        elif strat_single["strategy"] == "ma_slope":
            backtest_cmd += [
                "--window",
                str(strat_single.get("window", 120)),
                "--slope-window",
                str(strat_single.get("slope_window", 5)),
                "--enter-slope",
                str(strat_single.get("enter_slope", 0.0)),
                "--exit-slope",
                str(strat_single.get("exit_slope", 0.0)),
            ]
        elif strat_single["strategy"] == "bb_squeeze":
            backtest_cmd += [
                "--window",
                str(strat_single.get("window", 20)),
                "--n-std",
                str(strat_single.get("n_std", 2.0)),
                "--squeeze-q",
                str(strat_single.get("squeeze_q", 0.2)),
            ]
        elif strat_single["strategy"] == "supertrend":
            backtest_cmd += [
                "--atr-window",
                str(strat_single.get("atr_window", 10)),
                "--multiplier",
                str(strat_single.get("multiplier", 3.0)),
            ]

        run(
            backtest_cmd
        )

    # 2. 组合动量回测（使用本地 CSV）
    run(
        [
            "python",
            "sharecode/scripts/vectorbt_multi_momentum_from_dir.py",
            "--csv-dir",
            str(ROOT / "data"),
            "--glob",
            "*_daily_qfq.csv",
            "--lookback",
            str(strat_port["lookback"]),
            "--top-n",
            str(strat_port["top_n"]),
            "--rebalance-days",
            str(strat_port["rebalance_days"]),
            "--weight-scheme",
            strat_port["weight_scheme"],
            "--max-weight",
            str(strat_port["max_weight"]),
            "--init-cash",
            "100000",
            "--fees",
            "0.001",
            "--slippage",
            "0.0005",
        ]
    )


if __name__ == "__main__":
    main()

