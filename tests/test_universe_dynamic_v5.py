from tradebot_util.universe_dynamic_v5 import parse_universe_csv, update_dynamic_universe


def test_parse_universe_csv_recommended_format(tmp_path):
    path = tmp_path / "universe.csv"
    path.write_text(
        "ticker,name,sector,index_weight\n"
        "AXIA3,Axia Energia,Energia,19.77%\n"
        "SBSP3,Sabesp,Saneamento,18.85%\n"
        "EQTL3,Equatorial,Energia,11.81%\n",
        encoding="utf-8",
    )
    assets = parse_universe_csv(path)
    assert [a.ticker for a in assets] == ["AXIA3", "SBSP3", "EQTL3"]
    assert abs(sum(a.index_weight for a in assets) - 1.0) < 1e-9


def test_update_dynamic_universe_detects_added_removed(tmp_path):
    latest = tmp_path / "latest.csv"
    active = tmp_path / "active.csv"
    report = tmp_path / "report.csv"
    previous = tmp_path / "previous.csv"

    active.write_text(
        "ticker,name,sector,index_weight\n"
        "OLD3,Old,Setor,0.50\n"
        "KEEP3,Keep,Setor,0.50\n",
        encoding="utf-8",
    )
    latest.write_text(
        "ticker,name,sector,index_weight\n"
        "KEEP3,Keep,Setor,0.40\n"
        "NEW3,New,Setor,0.60\n",
        encoding="utf-8",
    )

    config = {
        "universe": {
            "latest_snapshot_path": str(latest),
            "active_universe_path": str(active),
            "previous_snapshot_path": str(previous),
            "update_report_path": str(report),
        }
    }

    result = update_dynamic_universe(config, source_csv=str(latest))
    assert result.added == ["NEW3"]
    assert result.removed == ["OLD3"]
    assert result.kept == ["KEEP3"]
    assert report.exists()
