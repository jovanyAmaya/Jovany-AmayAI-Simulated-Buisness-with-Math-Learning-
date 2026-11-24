import pandas as pd

from app import (
    EXPERIMENT_PATH,
    FIXTURE_PATH,
    PROGRESSION,
    build_run_signature,
    export_state_json,
    get_default_state,
    import_state_json,
    run_deterministic_model,
    run_reproducible_experiment,
)


def test_default_progression_is_fin():
    state = get_default_state()
    assert PROGRESSION == "FIN"
    assert state["progression"] == "FIN"


def test_zero_sales_edge_case():
    params = get_default_state()
    params["base_demand"] = 0.0
    params["starting_cash"] = 56000.0
    params["monthly_opex"] = 28000.0
    df, summary = run_deterministic_model(params)

    assert (df["units_sold"] == 0.0).all()
    assert (df["revenue"] == 0.0).all()
    assert summary["gross_margin_pct"] == 0.0
    assert summary["runway_months"] == 2


def test_capacity_cap_enforced():
    params = get_default_state()
    params["base_demand"] = 700.0
    params["monthly_growth_rate"] = 0.15
    params["max_capacity"] = 850.0
    df, summary = run_deterministic_model(params)

    assert df["units_sold"].max() == 850.0
    assert summary["capacity_capped"] is True


def test_duplicate_run_signature_and_rng_reproducibility():
    params = get_default_state()
    sig1 = build_run_signature(params)
    sig2 = build_run_signature(dict(params))
    assert sig1 == sig2

    res1 = run_reproducible_experiment(params, volatility=0.03, trials=100, seed=42)
    res2 = run_reproducible_experiment(params, volatility=0.03, trials=100, seed=42)
    pd.testing.assert_frame_equal(res1, res2)


def test_json_save_restore_preserves_fin_progression():
    original = get_default_state()
    original["unit_price"] = 135.0
    restored = import_state_json(export_state_json(original))

    assert restored == original
    assert restored["progression"] == "FIN"


def test_fixture_and_experiment_csvs_match_fin():
    fixture_df = pd.read_csv(FIXTURE_PATH)
    exp_df = pd.read_csv(EXPERIMENT_PATH)

    assert (fixture_df["progression"] == "FIN").all()
    assert (exp_df["progression"] == "FIN").all()