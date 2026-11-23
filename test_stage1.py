"""
Automated Stage 1 Acceptance & Numerical Verification Tests
Team ID: Team Lucas | Course: Algebra 2 | Pathway: MKT-1 | Level: Advanced
"""

import csv
import json
from decimal import Decimal

from app import (
    DEFAULT_FIXED_COSTS,
    DEFAULT_VARIABLE_COSTS,
    EXPECTED_TEAM_ID,
    algebra2_applied_analysis,
    algebra2_foundation_analysis,
    algebra2_advanced_shift_and_inequalities,
    calculate_monthly_metrics,
    commit_simulation_step,
    create_initial_state,
    export_snapshot_json,
    replay_fixture_rows,
    validate_and_load_snapshot_json,
)


def load_fixture_csv():
    with open("sample_data/monthly_fixture.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append(
                {
                    "month": r["month"],
                    "requested": int(r["requested"]),
                    "capacity_override": int(r["capacity_override"]),
                    "ad_cost": Decimal(r["ad_cost"]),
                }
            )
        return rows


def test_baseline_costs_and_capacity():
    state = create_initial_state()
    assert state["team_id"] == EXPECTED_TEAM_ID
    assert state["course"] == "Algebra 2"
    assert state["pathway_id"] == "MKT-1"
    assert state["selected_level"] == "Advanced"

    metrics = calculate_monthly_metrics(
        opening_cash=Decimal("4000.00"),
        price=Decimal("250.00"),
        requested=12,
        staff_hours=Decimal("80.00"),
        hours_per_unit=Decimal("8.00"),
        revision_hours_per_package=Decimal("0.00"),
        extra_revision_hourly_cost=Decimal("5.00"),
        variable_costs=DEFAULT_VARIABLE_COSTS,
        fixed_costs=DEFAULT_FIXED_COSTS,
    )
    assert metrics["capacity"] == 10
    assert metrics["sold"] == 10
    assert metrics["unserved_demand"] == 2
    assert metrics["variable_per_unit"] == Decimal("80.00")
    assert metrics["fixed_expense"] == Decimal("900.00")
    assert metrics["net_revenue"] == Decimal("2500.00")
    assert metrics["operating_profit"] == Decimal("800.00")
    assert metrics["ending_cash"] == Decimal("4800.00")


def test_mkt1_three_month_fixture_replay():
    rows = load_fixture_csv()
    final_state, results = replay_fixture_rows(create_initial_state(), rows)

    # 2027-01: Sold 10 | Revenue $2,500 | Total expense $1,700 | Profit $800 | Closing cash $4,800
    assert results[0]["sold"] == 10
    assert results[0]["revenue"] == Decimal("2500.00")
    assert results[0]["total_expense"] == Decimal("1700.00")
    assert results[0]["profit"] == Decimal("800.00")
    assert results[0]["closing_cash"] == Decimal("4800.00")

    # 2027-02: Sold 10 | Revenue $2,500 | Total expense $1,800 | Profit $700 | Closing cash $5,500
    assert results[1]["sold"] == 10
    assert results[1]["revenue"] == Decimal("2500.00")
    assert results[1]["total_expense"] == Decimal("1800.00")
    assert results[1]["profit"] == Decimal("700.00")
    assert results[1]["closing_cash"] == Decimal("5500.00")

    # 2027-03: Sold 7 | Revenue $1,750 | Total expense $1,460 | Profit $290 | Closing cash $5,790
    assert results[2]["sold"] == 7
    assert results[2]["revenue"] == Decimal("1750.00")
    assert results[2]["total_expense"] == Decimal("1460.00")
    assert results[2]["profit"] == Decimal("290.00")
    assert results[2]["closing_cash"] == Decimal("5790.00")
    assert Decimal(final_state["cash"]) == Decimal("5790.00")


def test_mkt1_extra_revisions_specific_test():
    # Handbook p. 100: extra revisions = 2 hrs/pkg -> capacity=8, unit=$90, rev=$2,000, var=$720, profit=$380
    metrics = calculate_monthly_metrics(
        opening_cash=Decimal("4000.00"),
        price=Decimal("250.00"),
        requested=12,
        staff_hours=Decimal("80.00"),
        hours_per_unit=Decimal("8.00"),
        revision_hours_per_package=Decimal("2.00"),
        extra_revision_hourly_cost=Decimal("5.00"),
        variable_costs=DEFAULT_VARIABLE_COSTS,
        fixed_costs=DEFAULT_FIXED_COSTS,
    )
    assert metrics["capacity"] == 8
    assert metrics["variable_per_unit"] == Decimal("90.00")
    assert metrics["net_revenue"] == Decimal("2000.00")
    assert metrics["variable_expense"] == Decimal("720.00")
    assert metrics["operating_profit"] == Decimal("380.00")


def test_zero_sales_and_loan_accounting_rules():
    zero_m = calculate_monthly_metrics(
        opening_cash=Decimal("4000.00"),
        price=Decimal("250.00"),
        requested=0,
        staff_hours=Decimal("80.00"),
        hours_per_unit=Decimal("8.00"),
        revision_hours_per_package=Decimal("0.00"),
        extra_revision_hourly_cost=Decimal("5.00"),
        variable_costs=DEFAULT_VARIABLE_COSTS,
        fixed_costs=DEFAULT_FIXED_COSTS,
    )
    assert zero_m["net_revenue"] == Decimal("0.00")
    assert zero_m["variable_expense"] == Decimal("0.00")
    assert zero_m["operating_profit"] == Decimal("-900.00")

    loan_m = calculate_monthly_metrics(
        opening_cash=Decimal("4000.00"),
        price=Decimal("250.00"),
        requested=0,
        staff_hours=Decimal("80.00"),
        hours_per_unit=Decimal("8.00"),
        revision_hours_per_package=Decimal("0.00"),
        extra_revision_hourly_cost=Decimal("5.00"),
        variable_costs=DEFAULT_VARIABLE_COSTS,
        fixed_costs=DEFAULT_FIXED_COSTS,
        loan_cash_received=Decimal("1500.00"),
    )
    assert loan_m["net_revenue"] == Decimal("0.00")
    assert loan_m["ending_cash"] == Decimal("4600.00")


def test_duplicate_run_and_snapshot_validation():
    state = create_initial_state()
    m = calculate_monthly_metrics(
        opening_cash=Decimal("4000.00"),
        price=Decimal("250.00"),
        requested=10,
        staff_hours=Decimal("80.00"),
        hours_per_unit=Decimal("8.00"),
        revision_hours_per_package=Decimal("0.00"),
        extra_revision_hourly_cost=Decimal("5.00"),
        variable_costs=DEFAULT_VARIABLE_COSTS,
        fixed_costs=DEFAULT_FIXED_COSTS,
    )
    ok1, _ = commit_simulation_step(state, "RUN-001", "2027-01-31", m, "Normal Mode")
    assert ok1 is True
    tx_count = len(state["ledger"])

    # Rerun same run_id -> must reject and not add transactions
    ok2, msg2 = commit_simulation_step(state, "RUN-001", "2027-01-31", m, "Normal Mode")
    assert ok2 is False
    assert "Duplicate run_id" in msg2
    assert len(state["ledger"]) == tx_count

    # Export and restore roundtrip
    exported = export_snapshot_json(state)
    ok_restore, _, restored = validate_and_load_snapshot_json(exported, state)
    assert ok_restore is True
    assert restored is not None
    assert restored["cash"] == state["cash"]
    assert restored["state_version"] == 2

    # Stale v1 snapshot rejected when current is v2
    stale_v1 = export_snapshot_json(create_initial_state())
    ok_stale, msg_stale, _ = validate_and_load_snapshot_json(stale_v1, state)
    assert ok_stale is False
    assert "stale" in msg_stale.lower()

    # Wrong team ID rejected
    bad_team = json.loads(exported)
    bad_team["team_id"] = "Team Rival"
    ok_team, msg_team, _ = validate_and_load_snapshot_json(json.dumps(bad_team), state)
    assert ok_team is False
    assert "team_id" in msg_team


def test_algebra2_course_adapter_checks():
    # Foundation: p0 = v and F > 0 -> no positive break-even
    f_no_be = algebra2_foundation_analysis(Decimal("80.00"), Decimal("80.00"), Decimal("900.00"), 10)
    assert f_no_be["exact_break_even"] is None
    assert f_no_be["is_feasible"] is False

    # Foundation: baseline break-even ceil(900 / 170) = 6 <= 10 (feasible)
    f_base = algebra2_foundation_analysis(Decimal("250.00"), Decimal("80.00"), Decimal("900.00"), 10)
    assert f_base["whole_break_even_units"] == 6
    assert f_base["is_feasible"] is True

    # Applied: demand at p = p0 equals D0 (12) before capacity cap
    app_res = algebra2_applied_analysis(Decimal("250.00"), 12, Decimal("80.00"), Decimal("900.00"), 10)
    assert app_res["demand_at_p0"] == 12.0

    # Advanced: extra shift adds floor(16/8)=2 units (capacity 10 -> 12) at cost 16*25=$400
    adv_res = algebra2_advanced_shift_and_inequalities(
        price=Decimal("250.00"),
        requested=12,
        staff_hours=Decimal("80.00"),
        hours_per_unit=Decimal("8.00"),
        revision_hours_per_package=Decimal("0.00"),
        variable_per_unit=Decimal("80.00"),
        fixed_expense=Decimal("900.00"),
        extra_shift_hours=Decimal("16.00"),
        extra_shift_hourly_rate=Decimal("25.00"),
        opening_cash=Decimal("4000.00"),
        min_cash_reserve=Decimal("1000.00"),
    )
    assert adv_res["base_capacity"] == 10
    assert adv_res["added_capacity"] == 2
    assert adv_res["shift_capacity"] == 12
    assert adv_res["added_shift_cost"] == Decimal("400.00")
    assert adv_res["feasible_max_s_int"] == 10


if __name__ == "__main__":
    test_baseline_costs_and_capacity()
    test_mkt1_three_month_fixture_replay()
    test_mkt1_extra_revisions_specific_test()
    test_zero_sales_and_loan_accounting_rules()
    test_duplicate_run_and_snapshot_validation()
    test_algebra2_course_adapter_checks()
    print("ALL 6 STAGE 1 ACCEPTANCE TEST SUITES PASSED!")
