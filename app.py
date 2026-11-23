"""
Career Venture Lab - Stage 1 Business Simulator
Team ID: Team Lucas
Course: Algebra 2 | Pathway ID: MKT-1 (Local-Business Marketing Agency)
Approved Challenge Level: Advanced

Stage 1 Scope (Student Handbook pp. 20, 58-60, 68, 98-102):
- Overview with persistent Math Skills & Challenge Level panel
- Inputs & Funding (Normal Mode vs. Fixture-Test Mode)
- Deterministic MKT-1 math & accounting engine using Decimal
- Algebra 2 Math Skills engine (Foundation, Applied, Advanced) with linked plots & tables
- Dated event ledger with daily/monthly/yearly aggregation and duplicate-run protection
- Durable Save/Load JSON with team_id and state_version validation
- Stage 2-4 modules clearly marked as unimplemented placeholders
"""

from __future__ import annotations

import copy
import json
import math
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go

try:
    import streamlit as st
except ModuleNotFoundError:  # Allows running pure math/ledger unit tests before pip install
    st = None

# ==============================================================================
# CONSTANTS & HANDBOOK DEFAULTS (MKT-1 / ALGEBRA 2 / ADVANCED)
# ==============================================================================

EXPECTED_TEAM_ID = "Team Lucas"
COURSE_NAME = "Algebra 2"
PATHWAY_ID = "MKT-1"
BUSINESS_NAME = "Local-business marketing agency"
DEFAULT_LEVEL = "Advanced"

TEACHER_APPROVED_SKILLS = [
    "Systems of Equations & Inequalities",
    "Piecewise Profit & Demand Modeling",
    "Capacity & Shift Sensitivity Analysis",
]

OFFERINGS_CATALOG = [
    {
        "offering_id": "OFF-MKT-01",
        "name": "Flyer design package",
        "unit": "campaign package",
        "price": "250.00",
        "demand_rule": "D0=12 at p0=$250; linear q(p)=max(0, 2*D0 - (D0/p0)*p)",
        "capacity_rule": "floor(staff_hours / (hours_per_unit + revision_hours_per_package))",
        "active_in_stage1": True,
    },
    {
        "offering_id": "OFF-MKT-02",
        "name": "Social campaign package",
        "unit": "campaign package",
        "price": "250.00",
        "demand_rule": "Requires separate cost/capacity allocation (Stage 2+)",
        "capacity_rule": "Disabled in Stage 1 to prevent duplicate revenue",
        "active_in_stage1": False,
    },
    {
        "offering_id": "OFF-MKT-03",
        "name": "Event promotion package",
        "unit": "campaign package",
        "price": "250.00",
        "demand_rule": "Requires separate cost/capacity allocation (Stage 2+)",
        "capacity_rule": "Disabled in Stage 1 to prevent duplicate revenue",
        "active_in_stage1": False,
    },
]

DEFAULT_VARIABLE_COSTS = {
    "designer_labor": Decimal("40.00"),
    "licensed_assets": Decimal("10.00"),
    "printing_delivery": Decimal("20.00"),
    "quality_revision_allowance": Decimal("10.00"),
}

DEFAULT_FIXED_COSTS = {
    "software": Decimal("250.00"),
    "workspace": Decimal("300.00"),
    "admin": Decimal("200.00"),
    "hosting": Decimal("150.00"),
}

FIXTURE_ROWS = [
    {"month": "2027-01", "requested": 12, "capacity_override": 10, "ad_cost": Decimal("0.00")},
    {"month": "2027-02", "requested": 13, "capacity_override": 10, "ad_cost": Decimal("100.00")},
    {"month": "2027-03", "requested": 11, "capacity_override": 7, "ad_cost": Decimal("0.00")},
]


# ==============================================================================
# DETERMINISTIC MONEY & STATE HELPERS
# ==============================================================================


def to_decimal(value: Any) -> Decimal:
    """Convert numeric or string values safely to 2-decimal-place USD Decimal."""
    if isinstance(value, Decimal):
        d = value
    else:
        d = Decimal(str(value))
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fmt_usd(value: Decimal | float | int) -> str:
    """Format monetary values cleanly in USD."""
    d = to_decimal(value)
    if d < 0:
        return f"-${abs(d):,.2f}"
    return f"${d:,.2f}"


def create_initial_state(
    team_id: str = EXPECTED_TEAM_ID,
    selected_level: str = DEFAULT_LEVEL,
    random_seed: int = 2027,
) -> Dict[str, Any]:
    """Create a fresh Stage 1 state matching Handbook pp. 58 & 98."""
    return {
        "team_id": team_id,
        "course": COURSE_NAME,
        "pathway_id": PATHWAY_ID,
        "business_name": BUSINESS_NAME,
        "snapshot_id": "SNAP-MKT1-V1",
        "state_version": 1,
        "simulation_date": "2027-01-31",
        "base_period": "monthly",
        "working_days": 20,
        "calendar_days": 30,
        "currency": "USD",
        "selected_level": selected_level,
        "level_by_skill": {
            skill: selected_level for skill in TEACHER_APPROVED_SKILLS
        },
        "random_seed": random_seed,
        "mode": "Normal Mode",
        "startup": {
            "owner_contribution": "6500.00",
            "equipment_assets": "1500.00",
            "pre_opening_expense": "1000.00",
            "opening_inventory": "0.00",
            "opening_cash": "4000.00",
            "opening_retained_earnings": "-1000.00",
        },
        "cash": "4000.00",
        "equipment_assets": "1500.00",
        "inventory_value": "0.00",
        "loan_debt": "0.00",
        "client_media_cash": "0.00",
        "client_media_liability": "0.00",
        "owner_equity": "6500.00",
        "retained_earnings": "-1000.00",
        "params": {
            "base_price": "250.00",
            "D0": 12,
            "requested_demand": 12,
            "staff_hours": "80.00",
            "hours_per_unit": "8.00",
            "revision_hours_per_package": "0.00",
            "extra_revision_hourly_cost": "5.00",
            "client_media_budget": "0.00",
            "own_marketing_expense": "0.00",
            "refund_amount": "0.00",
            "loan_cash_received": "0.00",
            "loan_principal_repayment": "0.00",
            "interest": "0.00",
            "additional_capex": "0.00",
            "new_owner_cash": "0.00",
            "extra_shift_hours": "16.00",
            "extra_shift_hourly_rate": "25.00",
            "min_cash_reserve": "1000.00",
        },
        "variable_costs": {k: str(v) for k, v in DEFAULT_VARIABLE_COSTS.items()},
        "fixed_costs": {k: str(v) for k, v in DEFAULT_FIXED_COSTS.items()},
        "not_modeled_baseline": {
            "borrowing_interest": "Disabled at baseline (explicitly modeled only when entered)",
            "refunds": "Disabled at baseline ($0.00)",
            "depreciation": "Disabled at baseline (Not Modeled)",
            "inventory": "Disabled at baseline ($0.00 — service agency)",
            "sales_tax": "Excluded / Not Modeled per handbook baseline rules",
        },
        "assumptions": [
            "All values are fictional teaching assumptions from Student Handbook MKT-1.",
            "Working days = 20 per month; calendar days = 30. Daily views are modeled allocations (monthly / working_days), never monthly / 30.",
            "Client media pass-through budgets are recorded as Cash + Liability until spent, never agency revenue or profit.",
            "Unmet demand (requested > capacity) is lost demand; no automatic backlog in Stage 1.",
        ],
        "sources": [
            "Career Venture Lab Student Handbook (Nov 2026), MKT Package pp. 98-102",
            "Career Venture Lab Student Handbook (Nov 2026), Algebra 2 Adapter p. 68 & Card MKT-1 p. 20",
        ],
        "offerings": copy.deepcopy(OFFERINGS_CATALOG),
        "ledger": [],
        "processed_run_ids": [],
        "campaigns": [],
        "decisions": [],
    }


# ==============================================================================
# CORE MKT-1 DETERMINISTIC ENGINE (HANDBOOK PP. 98-100)
# ==============================================================================


def validate_inputs(
    price: Decimal,
    requested: int,
    staff_hours: Decimal,
    hours_per_unit: Decimal,
    revision_hours: Decimal,
    extra_rev_cost: Decimal,
    var_costs: Dict[str, Decimal],
    fixed_costs: Dict[str, Decimal],
    own_marketing: Decimal = Decimal("0.00"),
    client_media_budget: Decimal = Decimal("0.00"),
    refund_amount: Decimal = Decimal("0.00"),
    loan_cash_received: Decimal = Decimal("0.00"),
    loan_principal_repayment: Decimal = Decimal("0.00"),
    interest: Decimal = Decimal("0.00"),
    additional_capex: Decimal = Decimal("0.00"),
    new_owner_cash: Decimal = Decimal("0.00"),
) -> List[str]:
    """Validate all inputs against MKT-1 constraints."""
    errors: List[str] = []
    if price <= Decimal("0.00"):
        errors.append("Package price must be strictly greater than $0.00 for the demand model.")
    if requested < 0 or int(requested) != requested:
        errors.append("Requested demand must be a nonnegative integer (>= 0).")
    if staff_hours < Decimal("0.00"):
        errors.append("Staff hours must be >= 0.")
    if hours_per_unit <= Decimal("0.00"):
        errors.append("Hours per unit must be strictly greater than 0.")
    if revision_hours < Decimal("0.00"):
        errors.append("Revision hours per package must be >= 0.")
    if extra_rev_cost < Decimal("0.00"):
        errors.append("Extra revision hourly cost must be >= 0.")
    for name, val in var_costs.items():
        if val < Decimal("0.00"):
            errors.append(f"Variable cost line '{name}' cannot be negative.")
    for name, val in fixed_costs.items():
        if val < Decimal("0.00"):
            errors.append(f"Fixed cost line '{name}' cannot be negative.")
    for label, val in [
        ("Own marketing expense", own_marketing),
        ("Client media budget", client_media_budget),
        ("Refund amount", refund_amount),
        ("Loan cash received", loan_cash_received),
        ("Loan principal repayment", loan_principal_repayment),
        ("Interest expense", interest),
        ("Additional capex", additional_capex),
        ("New owner cash", new_owner_cash),
    ]:
        if val < Decimal("0.00"):
            errors.append(f"{label} cannot be negative.")
    return errors


def calculate_monthly_metrics(
    opening_cash: Decimal,
    price: Decimal,
    requested: int,
    staff_hours: Decimal,
    hours_per_unit: Decimal,
    revision_hours_per_package: Decimal,
    extra_revision_hourly_cost: Decimal,
    variable_costs: Dict[str, Decimal],
    fixed_costs: Dict[str, Decimal],
    own_marketing_expense: Decimal = Decimal("0.00"),
    client_media_budget: Decimal = Decimal("0.00"),
    refund_amount: Decimal = Decimal("0.00"),
    loan_cash_received: Decimal = Decimal("0.00"),
    loan_principal_repayment: Decimal = Decimal("0.00"),
    interest: Decimal = Decimal("0.00"),
    additional_capex: Decimal = Decimal("0.00"),
    new_owner_cash: Decimal = Decimal("0.00"),
    capacity_override: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute the exact deterministic MKT-1 monthly calculation (Handbook p. 99).
    """
    errors = validate_inputs(
        price=price,
        requested=requested,
        staff_hours=staff_hours,
        hours_per_unit=hours_per_unit,
        revision_hours=revision_hours_per_package,
        extra_rev_cost=extra_revision_hourly_cost,
        var_costs=variable_costs,
        fixed_costs=fixed_costs,
        own_marketing=own_marketing_expense,
        client_media_budget=client_media_budget,
        refund_amount=refund_amount,
        loan_cash_received=loan_cash_received,
        loan_principal_repayment=loan_principal_repayment,
        interest=interest,
        additional_capex=additional_capex,
        new_owner_cash=new_owner_cash,
    )
    if errors:
        raise ValueError("; ".join(errors))

    effective_hours_per_pkg = hours_per_unit + revision_hours_per_package
    derived_capacity = int(math.floor(staff_hours / effective_hours_per_pkg))

    if capacity_override is not None:
        if capacity_override < 0:
            raise ValueError("capacity_override must be >= 0.")
        capacity = int(capacity_override)
        capacity_source = "Fixture Override (Test Mode)"
    else:
        capacity = derived_capacity
        capacity_source = "Derived from Designer Hours (Normal Mode)"

    sold = min(int(requested), capacity)
    unserved_demand = max(0, int(requested) - sold)

    base_var_unit = sum((to_decimal(v) for v in variable_costs.values()), Decimal("0.00"))
    extra_rev_var_unit = to_decimal(revision_hours_per_package * extra_revision_hourly_cost)
    variable_per_unit = to_decimal(base_var_unit + extra_rev_var_unit)

    gross_revenue = to_decimal(price * Decimal(sold))
    net_revenue = to_decimal(gross_revenue - refund_amount)
    variable_expense = to_decimal(Decimal(sold) * variable_per_unit)
    fixed_expense = to_decimal(sum((to_decimal(v) for v in fixed_costs.values()), Decimal("0.00")))
    own_marketing = to_decimal(own_marketing_expense)

    total_operating_expense = to_decimal(variable_expense + fixed_expense + own_marketing)
    operating_profit = to_decimal(net_revenue - total_operating_expense)
    net_profit = to_decimal(operating_profit - interest)

    ending_cash = to_decimal(
        opening_cash
        + net_revenue
        - variable_expense
        - fixed_expense
        - own_marketing
        - interest
        - loan_principal_repayment
        - additional_capex
        + new_owner_cash
        + loan_cash_received
    )

    hours_used = to_decimal(Decimal(sold) * effective_hours_per_pkg)
    total_available_hours = (
        to_decimal(Decimal(capacity) * effective_hours_per_pkg)
        if capacity_override is not None
        else to_decimal(staff_hours)
    )
    utilization_pct = (
        float((hours_used / total_available_hours) * Decimal("100"))
        if total_available_hours > Decimal("0.00")
        else 0.0
    )

    return {
        "effective_hours_per_pkg": effective_hours_per_pkg,
        "derived_capacity": derived_capacity,
        "capacity": capacity,
        "capacity_source": capacity_source,
        "requested": int(requested),
        "sold": sold,
        "unserved_demand": unserved_demand,
        "variable_per_unit": variable_per_unit,
        "gross_revenue": gross_revenue,
        "refund_amount": to_decimal(refund_amount),
        "net_revenue": net_revenue,
        "variable_expense": variable_expense,
        "fixed_expense": fixed_expense,
        "own_marketing_expense": own_marketing,
        "total_operating_expense": total_operating_expense,
        "operating_profit": operating_profit,
        "interest": to_decimal(interest),
        "net_profit": net_profit,
        "opening_cash": to_decimal(opening_cash),
        "ending_cash": ending_cash,
        "client_media_pass_through": to_decimal(client_media_budget),
        "hours_used": hours_used,
        "utilization_pct": round(utilization_pct, 2),
    }


def commit_simulation_step(
    state: Dict[str, Any],
    run_id: str,
    sim_date: str,
    metrics: Dict[str, Any],
    mode_label: str,
) -> Tuple[bool, str]:
    """
    Record an approved simulation step into the dated event ledger with duplicate-run
    protection (Handbook p. 58).
    """
    clean_run_id = run_id.strip()
    if not clean_run_id:
        return False, "A non-empty unique run_id is required before committing to the ledger."

    if clean_run_id in state["processed_run_ids"]:
        return (
            False,
            f"Duplicate run_id '{clean_run_id}' rejected: this simulation step is already recorded in the ledger.",
        )

    next_version = int(state["state_version"]) + 1
    tx_base = len(state["ledger"]) + 1

    entries: List[Dict[str, Any]] = []

    entries.append(
        {
            "transaction_id": f"TX-{tx_base:04d}",
            "run_id": clean_run_id,
            "date": sim_date,
            "event_type": "sale",
            "category": "Flyer design package revenue",
            "amount": str(metrics["net_revenue"]),
            "quantity": metrics["sold"],
            "unit_price": str(
                to_decimal(metrics["gross_revenue"] / Decimal(metrics["sold"]))
                if metrics["sold"] > 0
                else to_decimal(state["params"]["base_price"])
            ),
            "offering_id": "OFF-MKT-01",
            "campaign_id": "",
            "financing_type": "operating",
            "mode": mode_label,
            "state_version": next_version,
        }
    )
    tx_base += 1

    entries.append(
        {
            "transaction_id": f"TX-{tx_base:04d}",
            "run_id": clean_run_id,
            "date": sim_date,
            "event_type": "variable_expense",
            "category": "Package delivery & revision variable cost",
            "amount": str(-metrics["variable_expense"]),
            "quantity": metrics["sold"],
            "unit_price": str(metrics["variable_per_unit"]),
            "offering_id": "OFF-MKT-01",
            "campaign_id": "",
            "financing_type": "operating",
            "mode": mode_label,
            "state_version": next_version,
        }
    )
    tx_base += 1

    entries.append(
        {
            "transaction_id": f"TX-{tx_base:04d}",
            "run_id": clean_run_id,
            "date": sim_date,
            "event_type": "fixed_expense",
            "category": "Monthly fixed agency overhead",
            "amount": str(-metrics["fixed_expense"]),
            "quantity": 1,
            "unit_price": str(metrics["fixed_expense"]),
            "offering_id": "",
            "campaign_id": "",
            "financing_type": "operating",
            "mode": mode_label,
            "state_version": next_version,
        }
    )
    tx_base += 1

    if metrics["own_marketing_expense"] > Decimal("0.00"):
        entries.append(
            {
                "transaction_id": f"TX-{tx_base:04d}",
                "run_id": clean_run_id,
                "date": sim_date,
                "event_type": "marketing_expense",
                "category": "Own-agency advertising campaign",
                "amount": str(-metrics["own_marketing_expense"]),
                "quantity": 1,
                "unit_price": str(metrics["own_marketing_expense"]),
                "offering_id": "OFF-MKT-01",
                "campaign_id": f"CMP-{clean_run_id}",
                "financing_type": "operating",
                "mode": mode_label,
                "state_version": next_version,
            }
        )
        tx_base += 1

    params = state["params"]
    loan_in = to_decimal(params.get("loan_cash_received", "0.00"))
    principal_out = to_decimal(params.get("loan_principal_repayment", "0.00"))
    interest_out = to_decimal(params.get("interest", "0.00"))
    capex_out = to_decimal(params.get("additional_capex", "0.00"))
    owner_in = to_decimal(params.get("new_owner_cash", "0.00"))
    pass_through = to_decimal(metrics.get("client_media_pass_through", "0.00"))

    if loan_in > Decimal("0.00"):
        entries.append(
            {
                "transaction_id": f"TX-{tx_base:04d}",
                "run_id": clean_run_id,
                "date": sim_date,
                "event_type": "financing_loan_inflow",
                "category": "Simulated loan proceeds (Cash & Debt up; NOT revenue)",
                "amount": str(loan_in),
                "quantity": 1,
                "unit_price": str(loan_in),
                "offering_id": "",
                "campaign_id": "",
                "financing_type": "loan_proceeds",
                "mode": mode_label,
                "state_version": next_version,
            }
        )
        tx_base += 1

    if principal_out > Decimal("0.00"):
        entries.append(
            {
                "transaction_id": f"TX-{tx_base:04d}",
                "run_id": clean_run_id,
                "date": sim_date,
                "event_type": "financing_principal_repayment",
                "category": "Loan principal repayment (Reduces cash & debt; NOT operating expense)",
                "amount": str(-principal_out),
                "quantity": 1,
                "unit_price": str(principal_out),
                "offering_id": "",
                "campaign_id": "",
                "financing_type": "principal_repayment",
                "mode": mode_label,
                "state_version": next_version,
            }
        )
        tx_base += 1

    if interest_out > Decimal("0.00"):
        entries.append(
            {
                "transaction_id": f"TX-{tx_base:04d}",
                "run_id": clean_run_id,
                "date": sim_date,
                "event_type": "interest_expense",
                "category": "Loan interest expense",
                "amount": str(-interest_out),
                "quantity": 1,
                "unit_price": str(interest_out),
                "offering_id": "",
                "campaign_id": "",
                "financing_type": "interest",
                "mode": mode_label,
                "state_version": next_version,
            }
        )
        tx_base += 1

    if capex_out > Decimal("0.00"):
        entries.append(
            {
                "transaction_id": f"TX-{tx_base:04d}",
                "run_id": clean_run_id,
                "date": sim_date,
                "event_type": "capital_equipment_purchase",
                "category": "Equipment capital expenditure (Asset up, cash down; NOT operating expense)",
                "amount": str(-capex_out),
                "quantity": 1,
                "unit_price": str(capex_out),
                "offering_id": "",
                "campaign_id": "",
                "financing_type": "capex",
                "mode": mode_label,
                "state_version": next_version,
            }
        )
        tx_base += 1

    if owner_in > Decimal("0.00"):
        entries.append(
            {
                "transaction_id": f"TX-{tx_base:04d}",
                "run_id": clean_run_id,
                "date": sim_date,
                "event_type": "owner_contribution",
                "category": "Additional owner equity contribution (NOT sales revenue)",
                "amount": str(owner_in),
                "quantity": 1,
                "unit_price": str(owner_in),
                "offering_id": "",
                "campaign_id": "",
                "financing_type": "equity",
                "mode": mode_label,
                "state_version": next_version,
            }
        )
        tx_base += 1

    if pass_through > Decimal("0.00"):
        entries.append(
            {
                "transaction_id": f"TX-{tx_base:04d}",
                "run_id": clean_run_id,
                "date": sim_date,
                "event_type": "client_media_passthrough",
                "category": "Client media pass-through escrow (Cash + Liability; NOT agency revenue)",
                "amount": str(pass_through),
                "quantity": 1,
                "unit_price": str(pass_through),
                "offering_id": "OFF-MKT-01",
                "campaign_id": "",
                "financing_type": "passthrough_liability",
                "mode": mode_label,
                "state_version": next_version,
            }
        )

    state["ledger"].extend(entries)
    state["processed_run_ids"].append(clean_run_id)
    state["cash"] = str(metrics["ending_cash"])
    state["equipment_assets"] = str(to_decimal(state["equipment_assets"]) + capex_out)
    state["loan_debt"] = str(max(Decimal("0.00"), to_decimal(state["loan_debt"]) + loan_in - principal_out))
    state["owner_equity"] = str(to_decimal(state["owner_equity"]) + owner_in)
    state["retained_earnings"] = str(to_decimal(state["retained_earnings"]) + metrics["net_profit"])
    state["client_media_cash"] = str(to_decimal(state["client_media_cash"]) + pass_through)
    state["client_media_liability"] = str(to_decimal(state["client_media_liability"]) + pass_through)
    state["state_version"] = next_version
    state["snapshot_id"] = f"SNAP-MKT1-V{next_version}"
    state["simulation_date"] = sim_date

    return True, f"Committed run '{clean_run_id}' -> Advanced to state_version v{next_version} ({state['snapshot_id']})."


def replay_fixture_rows(
    base_state: Dict[str, Any],
    rows: List[Dict[str, Any]],
    run_prefix: str = "FIXTURE",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Reset to opening post-startup state and replay fixture rows sequentially.
    Uses capacity_override ONLY in Fixture-Test Mode.
    """
    sim_state = create_initial_state(
        team_id=base_state["team_id"],
        selected_level=base_state["selected_level"],
        random_seed=base_state["random_seed"],
    )
    sim_state["mode"] = "Fixture-Test Mode"

    var_costs = {k: to_decimal(v) for k, v in sim_state["variable_costs"].items()}
    fixed_costs = {k: to_decimal(v) for k, v in sim_state["fixed_costs"].items()}
    price = to_decimal(sim_state["params"]["base_price"])
    staff_hours = to_decimal(sim_state["params"]["staff_hours"])
    hours_per_unit = to_decimal(sim_state["params"]["hours_per_unit"])

    results_table: List[Dict[str, Any]] = []

    for row in rows:
        month_str = str(row["month"]).strip()
        req = int(row["requested"])
        cap_ov = int(row["capacity_override"])
        ad_cost = to_decimal(row["ad_cost"])
        opening = to_decimal(sim_state["cash"])

        metrics = calculate_monthly_metrics(
            opening_cash=opening,
            price=price,
            requested=req,
            staff_hours=staff_hours,
            hours_per_unit=hours_per_unit,
            revision_hours_per_package=Decimal("0.00"),
            extra_revision_hourly_cost=Decimal("5.00"),
            variable_costs=var_costs,
            fixed_costs=fixed_costs,
            own_marketing_expense=ad_cost,
            capacity_override=cap_ov,
        )

        sim_date = f"{month_str}-28" if len(month_str) == 7 else month_str
        run_id = f"{run_prefix}-{month_str}"
        ok, msg = commit_simulation_step(
            state=sim_state,
            run_id=run_id,
            sim_date=sim_date,
            metrics=metrics,
            mode_label="Fixture-Test Mode",
        )
        if not ok:
            raise RuntimeError(msg)

        results_table.append(
            {
                "month": month_str,
                "requested": req,
                "capacity_override": cap_ov,
                "sold": metrics["sold"],
                "revenue": metrics["net_revenue"],
                "total_expense": metrics["total_operating_expense"],
                "profit": metrics["operating_profit"],
                "closing_cash": metrics["ending_cash"],
            }
        )

    return sim_state, results_table


# ==============================================================================
# ALGEBRA 2 COURSE ADAPTER ENGINE (HANDBOOK PP. 20 & 68)
# ==============================================================================


def algebra2_foundation_analysis(
    price: Decimal,
    variable_per_unit: Decimal,
    fixed_expense: Decimal,
    capacity: int,
) -> Dict[str, Any]:
    """Foundation mode: linear revenue/cost and break-even feasibility."""
    unit_margin = price - variable_per_unit
    if unit_margin > Decimal("0.00"):
        exact_be = float(fixed_expense / unit_margin)
        whole_be_units = int(math.ceil(exact_be - 1e-12)) if fixed_expense > Decimal("0.00") else 0
        feasible = whole_be_units <= capacity
        status_label = (
            f"Feasible ({whole_be_units} units <= capacity {capacity})"
            if feasible
            else f"Infeasible ({whole_be_units} units > capacity {capacity})"
        )
        explanation = (
            f"Each package contributes {fmt_usd(unit_margin)} toward {fmt_usd(fixed_expense)} fixed overhead. "
            f"Exact break-even is {exact_be:.2f} packages -> {whole_be_units} whole packages ({status_label})."
        )
    else:
        exact_be = None
        whole_be_units = None
        feasible = False
        status_label = "No positive break-even (p0 <= v with F > 0)"
        explanation = (
            "Because package price does not exceed variable cost per package (p0 <= v) and fixed costs F > 0, "
            "selling more packages never covers fixed costs; no positive break-even exists."
        )

    points = []
    for s in range(0, capacity + 1):
        rev = to_decimal(price * Decimal(s))
        cost = to_decimal(fixed_expense + variable_per_unit * Decimal(s))
        prof = to_decimal(rev - cost)
        points.append(
            {
                "s_units": s,
                "revenue": float(rev),
                "cost": float(cost),
                "profit": float(prof),
            }
        )

    return {
        "equation_R": f"R(s) = {float(price):.2f}s",
        "equation_C": f"C(s) = {float(fixed_expense):.2f} + {float(variable_per_unit):.2f}s",
        "domain": f"0 <= s <= {capacity} (integer packages for actual sales)",
        "unit_contribution_margin": unit_margin,
        "exact_break_even": exact_be,
        "whole_break_even_units": whole_be_units,
        "is_feasible": feasible,
        "status_label": status_label,
        "explanation": explanation,
        "table": points,
    }


def algebra2_applied_analysis(
    p0: Decimal,
    D0: int,
    variable_per_unit: Decimal,
    fixed_expense: Decimal,
    capacity: int,
    candidate_prices: Optional[List[Decimal]] = None,
) -> Dict[str, Any]:
    """Applied mode: linear demand composition and piecewise profit."""
    p0_f = float(p0)
    d0_f = float(D0)
    slope = d0_f / p0_f
    intercept = 2.0 * d0_f
    max_p = 2.0 * p0_f

    def eval_price(p_val: float) -> Dict[str, Any]:
        q_raw = max(0.0, intercept - slope * p_val)
        s_cont = min(float(capacity), q_raw)
        s_int = min(int(capacity), int(math.floor(q_raw + 1e-9)))
        rev_cont = p_val * s_cont
        cost_cont = float(fixed_expense) + float(variable_per_unit) * s_cont
        prof_cont = rev_cont - cost_cont

        p_dec = to_decimal(p_val)
        rev_int = to_decimal(p_dec * Decimal(s_int))
        cost_int = to_decimal(fixed_expense + variable_per_unit * Decimal(s_int))
        prof_int = to_decimal(rev_int - cost_int)

        return {
            "price": p_val,
            "demand_q": round(q_raw, 4),
            "s_continuous": round(s_cont, 4),
            "s_integer": s_int,
            "revenue_continuous": round(rev_cont, 2),
            "cost_continuous": round(cost_cont, 2),
            "profit_continuous": round(prof_cont, 2),
            "revenue_integer": float(rev_int),
            "cost_integer": float(cost_int),
            "profit_integer": float(prof_int),
        }

    grid_prices = [round(i * (max_p / 25.0), 2) for i in range(26)]
    if p0_f not in grid_prices:
        grid_prices.append(p0_f)
        grid_prices.sort()
    curve_rows = [eval_price(p) for p in grid_prices]

    if candidate_prices is None:
        candidate_prices = [
            to_decimal(p0 * Decimal("0.80")),
            p0,
            to_decimal(p0 * Decimal("1.20")),
        ]
    comparison_rows = [eval_price(float(cp)) for cp in candidate_prices]

    return {
        "equation_demand": f"q(p) = max(0, {intercept:.2f} - {slope:.4f}p)",
        "equation_sales": f"s(p) = min({capacity}, q(p))",
        "domain": f"$0.00 <= p <= {fmt_usd(max_p)}",
        "demand_at_p0": round(max(0.0, intercept - slope * p0_f), 4),
        "curve_table": curve_rows,
        "comparison_table": comparison_rows,
    }


def algebra2_advanced_shift_and_inequalities(
    price: Decimal,
    requested: int,
    staff_hours: Decimal,
    hours_per_unit: Decimal,
    revision_hours_per_package: Decimal,
    variable_per_unit: Decimal,
    fixed_expense: Decimal,
    extra_shift_hours: Decimal,
    extra_shift_hourly_rate: Decimal,
    opening_cash: Decimal,
    min_cash_reserve: Decimal,
    include_quadratic_demo: bool = False,
) -> Dict[str, Any]:
    """Advanced mode: extra-shift comparison and system of inequalities."""
    eff_hours = hours_per_unit + revision_hours_per_package
    base_capacity = int(math.floor(staff_hours / eff_hours))
    added_capacity = int(math.floor(extra_shift_hours / eff_hours))
    shift_capacity = base_capacity + added_capacity
    added_shift_cost = to_decimal(extra_shift_hours * extra_shift_hourly_rate)
    shift_total_fixed = to_decimal(fixed_expense + added_shift_cost)

    base_sold = min(requested, base_capacity)
    base_rev = to_decimal(price * Decimal(base_sold))
    base_var = to_decimal(variable_per_unit * Decimal(base_sold))
    base_prof = to_decimal(base_rev - base_var - fixed_expense)
    base_end_cash = to_decimal(opening_cash + base_prof)

    shift_sold = min(requested, shift_capacity)
    shift_rev = to_decimal(price * Decimal(shift_sold))
    shift_var = to_decimal(variable_per_unit * Decimal(shift_sold))
    shift_prof = to_decimal(shift_rev - shift_var - shift_total_fixed)
    shift_end_cash = to_decimal(opening_cash + shift_prof)

    spendable_budget = max(Decimal("0.00"), opening_cash - min_cash_reserve)
    remaining_var_budget = spendable_budget - shift_total_fixed
    if variable_per_unit > Decimal("0.00"):
        budget_max_s_cont = float(remaining_var_budget / variable_per_unit)
    else:
        budget_max_s_cont = float(shift_capacity)

    budget_max_s_int = max(0, int(math.floor(budget_max_s_cont))) if remaining_var_budget >= Decimal("0.00") else 0
    feasible_max_s_int = max(0, min(shift_capacity, requested, budget_max_s_int))

    inequalities = [
        f"1. Designer Time: {float(eff_hours):.2f}s <= {float(staff_hours + extra_shift_hours):.2f} hrs  =>  s <= {shift_capacity} packages",
        f"2. Market Demand: s <= {requested} requested packages",
        f"3. Cash Reserve Safety: {float(shift_total_fixed):.2f} + {float(variable_per_unit):.2f}s <= {float(spendable_budget):.2f}  =>  s <= {budget_max_s_cont:.2f} (floor: {budget_max_s_int} packages)",
        "4. Non-negativity: s >= 0 (integer packages)",
    ]

    max_plot_s = max(shift_capacity + 2, requested + 2, 12)
    schedule_rows = []
    for s in range(0, max_plot_s + 1):
        rev_s = float(price * Decimal(s))
        cost_base_s = float(fixed_expense + variable_per_unit * Decimal(s))
        cost_shift_s = float(shift_total_fixed + variable_per_unit * Decimal(s))
        prof_base_s = rev_s - cost_base_s
        prof_shift_s = rev_s - cost_shift_s
        is_feasible_shift = (s <= shift_capacity) and (s <= requested) and (s <= budget_max_s_int)
        row_data = {
            "s_units": s,
            "revenue": round(rev_s, 2),
            "cost_baseline": round(cost_base_s, 2),
            "cost_extra_shift": round(cost_shift_s, 2),
            "profit_baseline": round(prof_base_s, 2),
            "profit_extra_shift": round(prof_shift_s, 2),
            "feasible_under_constraints": is_feasible_shift,
        }
        if include_quadratic_demo:
            quad_rev = max(0.0, (float(price) + 25.0) * s - 2.5 * (s ** 2))
            row_data["quadratic_demo_profit"] = round(quad_rev - cost_shift_s, 2)
        schedule_rows.append(row_data)

    return {
        "base_capacity": base_capacity,
        "added_capacity": added_capacity,
        "shift_capacity": shift_capacity,
        "added_shift_cost": added_shift_cost,
        "shift_total_fixed": shift_total_fixed,
        "base_sold": base_sold,
        "base_profit": base_prof,
        "base_ending_cash": base_end_cash,
        "shift_sold": shift_sold,
        "shift_profit": shift_prof,
        "shift_ending_cash": shift_end_cash,
        "profit_delta": to_decimal(shift_prof - base_prof),
        "feasible_max_s_int": feasible_max_s_int,
        "budget_max_s_cont": round(budget_max_s_cont, 2),
        "inequalities": inequalities,
        "schedule_table": schedule_rows,
        "interpretation_questions": [
            f"Q1 (Constraint Binding): With baseline capacity {base_capacity} and extra-shift capacity {shift_capacity}, which inequality (hours, demand, or cash reserve) limits your maximum feasible packages ({feasible_max_s_int}), and what happens to profit if requested demand falls below {shift_capacity}?",
            "Q2 (Extrapolation Limit): Why would extrapolating this linear shift model to 5 extra shifts per day fail in a real local-business marketing agency?",
        ],
    }


# ==============================================================================
# SNAPSHOT EXPORT / IMPORT & VALIDATION (HANDBOOK PP. 58-60)
# ==============================================================================


def export_snapshot_json(state: Dict[str, Any]) -> str:
    """Export the full structured Snapshot JSON matching the Handbook Data Contract."""
    payload = {
        "team_id": state["team_id"],
        "course": state["course"],
        "pathway_id": state["pathway_id"],
        "business_name": state["business_name"],
        "snapshot_id": state["snapshot_id"],
        "state_version": state["state_version"],
        "simulation_date": state["simulation_date"],
        "base_period": state["base_period"],
        "working_days": state["working_days"],
        "calendar_days": state["calendar_days"],
        "currency": state["currency"],
        "selected_level": state["selected_level"],
        "level_by_skill": state["level_by_skill"],
        "random_seed": state["random_seed"],
        "mode": state["mode"],
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "assumptions": state["assumptions"],
        "sources": state["sources"],
        "offerings": state["offerings"],
        "funding": [
            {
                "type": "owner_contribution",
                "amount": state["startup"]["owner_contribution"],
                "date": "2027-01-01",
            },
            {
                "type": "simulated_loan_debt",
                "amount": state["loan_debt"],
                "date": state["simulation_date"],
            },
        ],
        "cost_lines": {
            "variable_per_unit": state["variable_costs"],
            "monthly_fixed": state["fixed_costs"],
        },
        "capacity": {
            "staff_hours": state["params"]["staff_hours"],
            "hours_per_unit": state["params"]["hours_per_unit"],
            "revision_hours_per_package": state["params"]["revision_hours_per_package"],
        },
        "balances": {
            "cash": state["cash"],
            "equipment_assets": state["equipment_assets"],
            "inventory_value": state["inventory_value"],
            "loan_debt": state["loan_debt"],
            "client_media_cash": state["client_media_cash"],
            "client_media_liability": state["client_media_liability"],
            "owner_equity": state["owner_equity"],
            "retained_earnings": state["retained_earnings"],
        },
        "startup": state["startup"],
        "params": state["params"],
        "not_modeled_baseline": state["not_modeled_baseline"],
        "ledger": state["ledger"],
        "processed_run_ids": state["processed_run_ids"],
        "campaigns": state["campaigns"],
        "decisions": state["decisions"],
    }
    return json.dumps(payload, indent=2)


def validate_and_load_snapshot_json(
    raw_json: str,
    current_state: Dict[str, Any],
    expected_team_id: str = EXPECTED_TEAM_ID,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validate imported JSON snapshot against Handbook p. 58 transfer rules.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        return False, f"Invalid JSON format: {exc}", None

    if not isinstance(data, dict):
        return False, "Snapshot JSON root must be a JSON object.", None

    required_top_fields = [
        "team_id",
        "course",
        "pathway_id",
        "snapshot_id",
        "state_version",
        "simulation_date",
        "currency",
        "params",
        "ledger",
    ]
    missing = [f for f in required_top_fields if f not in data]
    if missing:
        return False, f"Rejected import: missing required fields: {', '.join(missing)}.", None

    if data["team_id"] != expected_team_id:
        return (
            False,
            f"Rejected import: team_id '{data['team_id']}' does not match '{expected_team_id}'.",
            None,
        )

    if data["pathway_id"] != PATHWAY_ID:
        return (
            False,
            f"Rejected import: pathway_id '{data['pathway_id']}' does not match '{PATHWAY_ID}'.",
            None,
        )

    try:
        imported_version = int(data["state_version"])
    except (TypeError, ValueError):
        return False, "Rejected import: state_version must be an integer.", None

    current_version = int(current_state["state_version"])
    if imported_version < current_version:
        return (
            False,
            f"Rejected stale snapshot (v{imported_version}): current business state is already at v{current_version}.",
            None,
        )

    seen_tx = set()
    for tx in data.get("ledger", []):
        tx_id = tx.get("transaction_id")
        if not tx_id or tx_id in seen_tx:
            return False, f"Rejected import: duplicate or missing transaction_id '{tx_id}'.", None
        seen_tx.add(tx_id)

    restored = create_initial_state(
        team_id=data["team_id"],
        selected_level=data.get("selected_level", DEFAULT_LEVEL),
        random_seed=int(data.get("random_seed", 2027)),
    )
    restored["snapshot_id"] = data["snapshot_id"]
    restored["state_version"] = imported_version
    restored["simulation_date"] = data["simulation_date"]
    restored["base_period"] = data.get("base_period", "monthly")
    restored["working_days"] = int(data.get("working_days", 20))
    restored["mode"] = data.get("mode", "Normal Mode")
    if "level_by_skill" in data:
        restored["level_by_skill"] = data["level_by_skill"]
    if "startup" in data:
        restored["startup"].update(data["startup"])
    if "balances" in data:
        for k, v in data["balances"].items():
            if k in restored:
                restored[k] = str(to_decimal(v))
    if "cost_lines" in data:
        if "variable_per_unit" in data["cost_lines"]:
            restored["variable_costs"] = {
                k: str(to_decimal(v)) for k, v in data["cost_lines"]["variable_per_unit"].items()
            }
        if "monthly_fixed" in data["cost_lines"]:
            restored["fixed_costs"] = {
                k: str(to_decimal(v)) for k, v in data["cost_lines"]["monthly_fixed"].items()
            }
    restored["params"].update(data["params"])
    restored["ledger"] = data["ledger"]
    restored["processed_run_ids"] = data.get(
        "processed_run_ids",
        list(dict.fromkeys(tx["run_id"] for tx in data["ledger"] if "run_id" in tx)),
    )
    restored["campaigns"] = data.get("campaigns", [])
    restored["decisions"] = data.get("decisions", [])

    return (
        True,
        f"Restored snapshot '{restored['snapshot_id']}' (state_version v{imported_version}) with {len(restored['ledger'])} ledger entries.",
        restored,
    )


def aggregate_ledger_views(ledger: List[Dict[str, Any]], working_days: int = 20) -> Dict[str, pd.DataFrame]:
    """
    Build Daily (modeled allocation = monthly / working_days), Monthly, and Yearly
    views from the single dated ledger.
    """
    if not ledger:
        empty = pd.DataFrame()
        return {"daily": empty, "monthly": empty, "yearly": empty}

    df = pd.DataFrame(ledger).copy()
    df["amount_num"] = df["amount"].apply(lambda x: float(to_decimal(x)))
    df["month"] = df["date"].str.slice(0, 7)
    df["year"] = df["date"].str.slice(0, 4)

    monthly = (
        df.groupby(["month", "event_type"], as_index=False)["amount_num"]
        .sum()
        .pivot(index="month", columns="event_type", values="amount_num")
        .fillna(0.0)
        .reset_index()
    )
    monthly["net_cash_delta"] = monthly.drop(columns=["month"]).sum(axis=1)

    yearly = (
        df.groupby(["year", "event_type"], as_index=False)["amount_num"]
        .sum()
        .pivot(index="year", columns="event_type", values="amount_num")
        .fillna(0.0)
        .reset_index()
    )
    yearly["net_cash_delta"] = yearly.drop(columns=["year"]).sum(axis=1)

    daily = monthly.copy()
    numeric_cols = [c for c in daily.columns if c != "month"]
    for c in numeric_cols:
        daily[c] = (daily[c] / float(working_days)).round(2)
    daily.insert(
        1,
        "allocation_basis",
        f"Modeled daily allocation (Monthly / {working_days} working days — NOT observed daily logs)",
    )

    return {"daily": daily, "monthly": monthly, "yearly": yearly}


# ==============================================================================
# STREAMLIT USER INTERFACE (STAGE 1)
# ==============================================================================


def init_session() -> None:
    if "cvl_state" not in st.session_state:
        st.session_state["cvl_state"] = create_initial_state()
    if "fixture_replay_results" not in st.session_state:
        st.session_state["fixture_replay_results"] = None


def render_persistent_math_panel(state: Dict[str, Any]) -> None:
    """Persistent Math Skills & Challenge Level panel."""
    level = state["selected_level"]
    params = state["params"]
    p0 = to_decimal(params["base_price"])
    d0 = int(params["D0"])
    staff_h = to_decimal(params["staff_hours"])
    h_unit = to_decimal(params["hours_per_unit"])
    rev_h = to_decimal(params["revision_hours_per_package"])
    extra_rev_c = to_decimal(params["extra_revision_hourly_cost"])
    v_total = sum((to_decimal(x) for x in state["variable_costs"].values()), Decimal("0.00")) + rev_h * extra_rev_c
    f_total = sum((to_decimal(x) for x in state["fixed_costs"].values()), Decimal("0.00"))
    cap = int(math.floor(staff_h / (h_unit + rev_h)))

    with st.container(border=True):
        st.markdown(
            f"### Math Skills & Challenge Level Panel — `{state['course']}` | Pathway `{state['pathway_id']}` | Level: **{level}**"
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Team ID", state["team_id"])
        c2.metric("State Version", f"v{state['state_version']} ({state['snapshot_id']})")
        c3.metric("Simulation Date", state["simulation_date"])
        c4.metric("Derived Capacity", f"{cap} packages/mo")

        if level == "Foundation":
            st.info(
                "**Active Skill (Foundation):** Linear Revenue, Cost & Break-Even Feasibility\n\n"
                f"**Equations:** $R(s) = {float(p0):.2f}s$, $C(s) = {float(f_total):.2f} + {float(v_total):.2f}s$, "
                f"Break-even $s_{{BE}} = \\frac{{{float(f_total):.2f}}}{{{float(p0):.2f} - {float(v_total):.2f}}}$\n\n"
                f"**Domain & Units:** $0 \\le s \\le {cap}$ packages/month; $R, C$ in USD ($); $s$ in whole campaign packages."
            )
        elif level == "Applied":
            slope = d0 / float(p0)
            st.info(
                "**Active Skill (Applied):** Composed Price-Demand & Piecewise Profit Modeling\n\n"
                f"**Equations:** $q(p) = \\max(0, {2*d0} - {slope:.4f}p)$, completed $s(p) = \\min({cap}, q(p))$, $P(p) = p \\cdot s(p) - ({float(f_total):.2f} + {float(v_total):.2f}s(p))$\n\n"
                f"**Domain & Units:** Price domain $\\$0.00 \\le p \\le {fmt_usd(p0 * 2)}$; continuous relaxation plotted vs. floored integer packages for ledger transactions."
            )
        else:
            extra_h = to_decimal(params["extra_shift_hours"])
            extra_rate = to_decimal(params["extra_shift_hourly_rate"])
            st.info(
                "**Active Skill (Advanced — Teacher-Approved Default):** Systems of Inequalities & Extra-Shift Sensitivity\n\n"
                f"**Equations:** Baseline capacity $s \\le \\lfloor {float(staff_h):.1f}/{float(h_unit + rev_h):.1f} \\rfloor = {cap}$; "
                f"Extra shift adds $\\lfloor {float(extra_h):.1f}/{float(h_unit + rev_h):.1f} \\rfloor$ packages at cost $+{fmt_usd(extra_h * extra_rate)}$.\n\n"
                "**Assumptions & Domain:** Integer packages $s \\ge 0$; unit variable cost held fixed during shift/price sensitivity; all starter figures are fictional teaching defaults."
            )

        with st.expander("Change Challenge Level (Requires Teacher Approval Confirmation)"):
            st.caption(
                "Handbook Rule (p. 6): Changing a level changes equations, inputs, visualizations, and assessment evidence. "
                "Confirm teacher approval before switching levels."
            )
            col_l1, col_l2 = st.columns([2, 1])
            chosen_level = col_l1.selectbox(
                "Select Algebra 2 Challenge Level",
                options=["Foundation", "Applied", "Advanced"],
                index=["Foundation", "Applied", "Advanced"].index(level),
                key="level_selector_widget",
            )
            teacher_ok = col_l2.checkbox(
                "Teacher approved this level change",
                value=False,
                key="teacher_approved_level_chk",
            )
            if st.button("Apply Challenge Level", key="apply_level_btn"):
                if chosen_level == level:
                    st.info(f"Already set to {level}.")
                elif not teacher_ok:
                    st.warning("Level change blocked: check 'Teacher approved this level change' first.")
                else:
                    state["selected_level"] = chosen_level
                    for sk in state["level_by_skill"]:
                        state["level_by_skill"][sk] = chosen_level
                    st.success(f"Challenge level updated to {chosen_level}.")
                    st.rerun()


def render_overview_page(state: Dict[str, Any]) -> None:
    st.title("Career Venture Lab — Stage 1 Business Simulator")
    st.caption(
        f"**{state['team_id']}** | Course: **{state['course']}** | Pathway: **{state['pathway_id']} ({state['business_name']})** | "
        "Status: **Stage 1 Active Build** (Deterministic Math, Ledger, Save/Load JSON & Fixture Tests)"
    )

    render_persistent_math_panel(state)

    st.subheader("Plain-Language Agency Snapshot (Current Approved State)")
    cash = to_decimal(state["cash"])
    equip = to_decimal(state["equipment_assets"])
    debt = to_decimal(state["loan_debt"])
    equity = to_decimal(state["owner_equity"])
    ret_earn = to_decimal(state["retained_earnings"])
    client_escrow = to_decimal(state["client_media_liability"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Spendable Agency Cash", fmt_usd(cash), help="Cash available for agency operations (excludes client pass-through escrow).")
    m2.metric("Equipment Assets", fmt_usd(equip), help="Computer & design equipment ($1,500 startup asset; not re-expensed).")
    m3.metric("Retained Earnings", fmt_usd(ret_earn), help="Starts at -$1,000 from pre-opening software/setup expense, plus cumulative net profit.")
    m4.metric("Ledger Entries Recorded", str(len(state["ledger"])), help="Total immutable transaction rows in the dated event ledger.")

    if client_escrow > Decimal("0.00") or debt > Decimal("0.00"):
        c_extra1, c_extra2, c_extra3 = st.columns(3)
        c_extra1.metric("Owner Equity", fmt_usd(equity))
        c_extra2.metric("Simulated Loan Debt", fmt_usd(debt))
        c_extra3.metric("Client Pass-Through Liability", fmt_usd(client_escrow))

    st.markdown("#### Accounting & Simulation Guardrails Active in Stage 1")
    st.markdown(
        "- **Cash vs. Profit Separated:** Startup owner contributions (`$6,500`), loan proceeds, and capital equipment (`$1,500`) affect cash/assets/debt—never sales revenue or operating expense.\n"
        "- **Demand vs. Completed Sales:** Requested packages exceeding monthly designer capacity become unserved (lost) demand, never recognized revenue.\n"
        "- **Pass-Through Client Ad Budgets:** Treated as Cash + Liability until spent, never counted as agency fee profit.\n"
        "- **Not Modeled at Baseline:** Depreciation, inventory, sales tax, and automatic interest/refunds remain disabled unless explicitly entered."
    )


def render_inputs_and_funding_page(state: Dict[str, Any]) -> None:
    st.header("Inputs & Funding — Normal Mode vs. Fixture-Test Mode")
    render_persistent_math_panel(state)

    mode = st.radio(
        "Select Operating Mode",
        options=["Normal Mode", "Fixture-Test Mode"],
        index=0 if state["mode"] == "Normal Mode" else 1,
        horizontal=True,
        help="Normal Mode computes capacity from designer staff hours. Fixture-Test Mode replays monthly_fixture.csv with explicit capacity overrides.",
    )
    state["mode"] = mode

    if mode == "Fixture-Test Mode":
        st.warning(
            "**FIXTURE-TEST MODE ACTIVE (Handbook p. 100):** This mode uses explicit `capacity_override` values from "
            "`sample_data/monthly_fixture.csv` strictly to verify ledger math. Do NOT mix Fixture-Test Mode runs with Normal Mode runs."
        )
        fixture_df = pd.DataFrame(FIXTURE_ROWS)
        st.dataframe(fixture_df, use_container_width=True)

        col_f1, col_f2 = st.columns(2)
        if col_f1.button("Reset to Post-Startup Opening State ($4,000 Cash) & Replay All 3 Fixture Months", type="primary"):
            new_state, replay_table = replay_fixture_rows(state, FIXTURE_ROWS, run_prefix="FIXTURE")
            st.session_state["cvl_state"] = new_state
            st.session_state["fixture_replay_results"] = replay_table
            st.success("Reset to $4,000 opening cash and replayed 2027-01, 2027-02, and 2027-03!")
            st.rerun()

        if col_f2.button("Reset Business to Fresh Post-Startup Opening State ($4,000 Cash)"):
            st.session_state["cvl_state"] = create_initial_state(
                team_id=state["team_id"],
                selected_level=state["selected_level"],
                random_seed=state["random_seed"],
            )
            st.session_state["fixture_replay_results"] = None
            st.success("Business reset to initial post-startup balances (state_version v1, cash $4,000.00).")
            st.rerun()

        if st.session_state.get("fixture_replay_results"):
            st.subheader("Fixture Replay Output vs. Handbook Expected Results")
            rep_df = pd.DataFrame(st.session_state["fixture_replay_results"])
            for col in ["revenue", "total_expense", "profit", "closing_cash"]:
                rep_df[col] = rep_df[col].apply(fmt_usd)
            st.dataframe(rep_df, use_container_width=True)
        return

    st.subheader("1. Startup Financing & Opening Balances (Fictional Teaching Defaults)")
    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    s_col1.metric("Owner Contribution", fmt_usd(state["startup"]["owner_contribution"]))
    s_col2.metric("Equipment Assets", fmt_usd(state["startup"]["equipment_assets"]))
    s_col3.metric("Pre-Opening Expense", fmt_usd(state["startup"]["pre_opening_expense"]))
    s_col4.metric("Post-Startup Opening Cash", fmt_usd(state["startup"]["opening_cash"]))

    st.subheader("2. Monthly Pricing, Demand & Capacity Inputs (Scenario Preview)")
    params = state["params"]
    c1, c2, c3 = st.columns(3)
    price_in = c1.number_input(
        "Package Price ($ / campaign package)",
        min_value=1.0,
        max_value=5000.0,
        value=float(params["base_price"]),
        step=10.0,
    )
    req_in = c2.number_input(
        "Requested Demand (packages / month)",
        min_value=0,
        max_value=500,
        value=int(params["requested_demand"]),
        step=1,
    )
    staff_h_in = c3.number_input(
        "Designer Staff Hours / Month",
        min_value=0.0,
        max_value=1000.0,
        value=float(params["staff_hours"]),
        step=4.0,
    )

    c4, c5, c6 = st.columns(3)
    h_unit_in = c4.number_input(
        "Base Hours per Package",
        min_value=0.5,
        max_value=100.0,
        value=float(params["hours_per_unit"]),
        step=0.5,
    )
    rev_h_in = c5.number_input(
        "Extra Revision Hours / Package",
        min_value=0.0,
        max_value=40.0,
        value=float(params["revision_hours_per_package"]),
        step=0.5,
        help="Handbook test: setting extra revisions = 2 hrs/pkg reduces capacity from 10 to 8 and adds $10/unit variable cost.",
    )
    rev_cost_in = c6.number_input(
        "Extra Revision Hourly Cost ($ / hr)",
        min_value=0.0,
        max_value=200.0,
        value=float(params["extra_revision_hourly_cost"]),
        step=1.0,
    )

    st.subheader("3. Editable Variable & Monthly Fixed Cost Lines")
    vc_col, fc_col = st.columns(2)
    with vc_col:
        st.markdown("**Per-Delivered-Package Variable Costs**")
        new_var_costs: Dict[str, Decimal] = {}
        for k, v in state["variable_costs"].items():
            val = st.number_input(
                f"{k.replace('_', ' ').title()} ($/pkg)",
                min_value=0.0,
                max_value=2000.0,
                value=float(v),
                step=1.0,
                key=f"vc_{k}",
            )
            new_var_costs[k] = to_decimal(val)

    with fc_col:
        st.markdown("**Monthly Fixed Overhead Costs**")
        new_fixed_costs: Dict[str, Decimal] = {}
        for k, v in state["fixed_costs"].items():
            val = st.number_input(
                f"{k.replace('_', ' ').title()} ($/mo)",
                min_value=0.0,
                max_value=10000.0,
                value=float(v),
                step=10.0,
                key=f"fc_{k}",
            )
            new_fixed_costs[k] = to_decimal(val)

    with st.expander("4. Optional Marketing, Financing, Capex & Client Pass-Through Controls"):
        oc1, oc2, oc3 = st.columns(3)
        own_mkt_in = oc1.number_input(
            "Own-Agency Advertising Expense ($)",
            min_value=0.0,
            max_value=50000.0,
            value=float(params["own_marketing_expense"]),
            step=25.0,
        )
        client_media_in = oc2.number_input(
            "Client Pass-Through Media Budget ($)",
            min_value=0.0,
            max_value=100000.0,
            value=float(params["client_media_budget"]),
            step=50.0,
            help="Held as Cash + Liability until spent; never counted as agency revenue or profit.",
        )
        refund_in = oc3.number_input(
            "Customer Refunds ($)",
            min_value=0.0,
            max_value=50000.0,
            value=float(params["refund_amount"]),
            step=25.0,
        )

        fc1, fc2, fc3, fc4 = st.columns(4)
        loan_in = fc1.number_input(
            "Simulated Loan Proceeds ($)",
            min_value=0.0,
            max_value=100000.0,
            value=float(params["loan_cash_received"]),
            step=100.0,
            help="Increases Cash and Debt; NOT sales revenue.",
        )
        principal_in = fc2.number_input(
            "Loan Principal Repayment ($)",
            min_value=0.0,
            max_value=100000.0,
            value=float(params["loan_principal_repayment"]),
            step=50.0,
            help="Reduces Cash and Debt; NOT operating expense.",
        )
        interest_in = fc3.number_input(
            "Loan Interest Expense ($)",
            min_value=0.0,
            max_value=20000.0,
            value=float(params["interest"]),
            step=10.0,
        )
        capex_in = fc4.number_input(
            "Additional Equipment Capex ($)",
            min_value=0.0,
            max_value=50000.0,
            value=float(params["additional_capex"]),
            step=100.0,
            help="Cash outflow that increases Equipment Assets; NOT ordinary operating expense.",
        )

    params["base_price"] = str(to_decimal(price_in))
    params["requested_demand"] = int(req_in)
    params["staff_hours"] = str(to_decimal(staff_h_in))
    params["hours_per_unit"] = str(to_decimal(h_unit_in))
    params["revision_hours_per_package"] = str(to_decimal(rev_h_in))
    params["extra_revision_hourly_cost"] = str(to_decimal(rev_cost_in))
    params["own_marketing_expense"] = str(to_decimal(own_mkt_in))
    params["client_media_budget"] = str(to_decimal(client_media_in))
    params["refund_amount"] = str(to_decimal(refund_in))
    params["loan_cash_received"] = str(to_decimal(loan_in))
    params["loan_principal_repayment"] = str(to_decimal(principal_in))
    params["interest"] = str(to_decimal(interest_in))
    params["additional_capex"] = str(to_decimal(capex_in))
    state["variable_costs"] = {k: str(v) for k, v in new_var_costs.items()}
    state["fixed_costs"] = {k: str(v) for k, v in new_fixed_costs.items()}

    preview = calculate_monthly_metrics(
        opening_cash=to_decimal(state["cash"]),
        price=to_decimal(price_in),
        requested=int(req_in),
        staff_hours=to_decimal(staff_h_in),
        hours_per_unit=to_decimal(h_unit_in),
        revision_hours_per_package=to_decimal(rev_h_in),
        extra_revision_hourly_cost=to_decimal(rev_cost_in),
        variable_costs=new_var_costs,
        fixed_costs=new_fixed_costs,
        own_marketing_expense=to_decimal(own_mkt_in),
        client_media_budget=to_decimal(client_media_in),
        refund_amount=to_decimal(refund_in),
        loan_cash_received=to_decimal(loan_in),
        loan_principal_repayment=to_decimal(principal_in),
        interest=to_decimal(interest_in),
        additional_capex=to_decimal(capex_in),
    )

    st.subheader("5. Live Scenario Preview (Not Yet Committed to Ledger)")
    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Monthly Capacity", f"{preview['capacity']} pkgs", help=preview["capacity_source"])
    p2.metric("Completed Sales", f"{preview['sold']} pkgs", delta=f"-{preview['unserved_demand']} unserved" if preview["unserved_demand"] > 0 else "0 unserved", delta_color="off")
    p3.metric("Net Revenue", fmt_usd(preview["net_revenue"]))
    p4.metric("Operating Profit", fmt_usd(preview["operating_profit"]))
    p5.metric("Projected Ending Cash", fmt_usd(preview["ending_cash"]))

    with st.container(border=True):
        st.markdown("**Approve & Commit Step to Dated Ledger (Duplicate-Run Protected)**")
        rc1, rc2, rc3 = st.columns([2, 2, 1])
        run_id_in = rc1.text_input(
            "Unique Run ID",
            value=f"RUN-V{state['state_version']}-M{len(state['processed_run_ids']) + 1:02d}",
            key="commit_run_id_input",
        )
        sim_date_in = rc2.text_input(
            "Simulation Period End Date (YYYY-MM-DD)",
            value=state["simulation_date"],
            key="commit_sim_date_input",
        )
        student_approve = rc3.checkbox("Student Approved", value=False, key="commit_approve_chk")

        if st.button("Commit Approved Month to Ledger", type="primary"):
            if not student_approve:
                st.warning("Human approval gate: check 'Student Approved' before advancing the simulation state.")
            else:
                ok, msg = commit_simulation_step(
                    state=state,
                    run_id=run_id_in,
                    sim_date=sim_date_in,
                    metrics=preview,
                    mode_label="Normal Mode",
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def render_algebra2_page(state: Dict[str, Any]) -> None:
    st.header("Algebra 2 Course Math & Linked Visuals — Pathway MKT-1")
    render_persistent_math_panel(state)

    level = state["selected_level"]
    params = state["params"]
    p0 = to_decimal(params["base_price"])
    d0 = int(params["D0"])
    requested = int(params["requested_demand"])
    staff_h = to_decimal(params["staff_hours"])
    h_unit = to_decimal(params["hours_per_unit"])
    rev_h = to_decimal(params["revision_hours_per_package"])
    extra_rev_c = to_decimal(params["extra_revision_hourly_cost"])
    v_total = sum((to_decimal(x) for x in state["variable_costs"].values()), Decimal("0.00")) + rev_h * extra_rev_c
    f_total = sum((to_decimal(x) for x in state["fixed_costs"].values()), Decimal("0.00"))
    capacity = int(math.floor(staff_h / (h_unit + rev_h)))
    opening_cash = to_decimal(state["cash"])

    if level == "Foundation":
        st.subheader("Foundation Mode: Break-Even & Capacity Feasibility")
        res = algebra2_foundation_analysis(p0, v_total, f_total, capacity)
        st.markdown(f"**Equations:** `{res['equation_R']}` and `{res['equation_C']}` | **Domain:** `{res['domain']}`")
        st.success(res["explanation"]) if res["is_feasible"] else st.warning(res["explanation"])

        df = pd.DataFrame(res["table"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["s_units"], y=df["revenue"], mode="lines+markers", name="Revenue R(s) ($)", line=dict(width=3)))
        fig.add_trace(go.Scatter(x=df["s_units"], y=df["cost"], mode="lines+markers", name="Total Cost C(s) ($)", line=dict(width=3, dash="dash")))
        fig.add_trace(go.Scatter(x=df["s_units"], y=df["profit"], mode="lines+markers", name="Operating Profit ($)", line=dict(width=2, dash="dot")))
        fig.add_hline(y=0, line_width=1.5, line_color="black", annotation_text="Zero Profit Line ($0)")
        if res["exact_break_even"] is not None and res["exact_break_even"] <= capacity:
            fig.add_vline(x=res["exact_break_even"], line_dash="dashdot", annotation_text=f"Break-Even ({res['exact_break_even']:.2f})")
        fig.update_layout(
            title=f"Foundation Break-Even & Capacity Plot ({state['team_id']} | {state['snapshot_id']} | {state['simulation_date']})",
            xaxis_title="Completed Packages s (units)",
            yaxis_title="Amount (USD $)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "Download Linked Chart Data + Assumptions (CSV)",
            data=df.to_csv(index=False),
            file_name=f"mkt1_foundation_{state['snapshot_id']}.csv",
            mime="text/csv",
        )

    elif level == "Applied":
        st.subheader("Applied Mode: Composed Price-Demand & Piecewise Profit")
        res = algebra2_applied_analysis(p0, d0, v_total, f_total, capacity)
        st.markdown(f"**Demand:** `{res['equation_demand']}` | **Capped Sales:** `{res['equation_sales']}` | **Domain:** `{res['domain']}`")
        st.caption(
            f"Check at p = p0 ({fmt_usd(p0)}): q(p0) = {res['demand_at_p0']} requested packages before capacity cap ({capacity}). "
            "Continuous relaxation is plotted smoothly; actual simulated ledger transactions floor completed integer packages."
        )

        df = pd.DataFrame(res["curve_table"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["price"], y=df["revenue_continuous"], mode="lines", name="Continuous Revenue R(p) ($)", line=dict(width=3)))
        fig.add_trace(go.Scatter(x=df["price"], y=df["cost_continuous"], mode="lines", name="Continuous Cost C(s(p)) ($)", line=dict(width=3, dash="dash")))
        fig.add_trace(go.Scatter(x=df["price"], y=df["profit_continuous"], mode="lines", name="Continuous Profit P(p) ($)", line=dict(width=3, dash="dot")))
        fig.add_trace(go.Scatter(x=df["price"], y=df["profit_integer"], mode="markers", name="Integer-Floored Profit ($)", marker=dict(size=8, symbol="diamond")))
        fig.add_hline(y=0, line_width=1.5, line_color="black", annotation_text="Zero Profit Line ($0)")
        fig.update_layout(
            title=f"Applied Piecewise Profit & Price-Demand ({state['team_id']} | {state['snapshot_id']})",
            xaxis_title="Package Price p (USD $)",
            yaxis_title="Amount (USD $)",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Three Feasible Price Comparison Table (Continuous vs. Integer Transaction Rounding)**")
        st.dataframe(pd.DataFrame(res["comparison_table"]), use_container_width=True)

    else:
        st.subheader("Advanced Mode: Systems of Inequalities & Extra-Shift Sensitivity")
        sc1, sc2, sc3, sc4 = st.columns(4)
        extra_h_in = sc1.number_input(
            "Extra Shift Hours / Month",
            min_value=0.0,
            max_value=160.0,
            value=float(params["extra_shift_hours"]),
            step=4.0,
        )
        extra_rate_in = sc2.number_input(
            "Extra Shift Hourly Rate ($/hr)",
            min_value=0.0,
            max_value=200.0,
            value=float(params["extra_shift_hourly_rate"]),
            step=5.0,
        )
        reserve_in = sc3.number_input(
            "Minimum Cash Reserve ($)",
            min_value=0.0,
            max_value=20000.0,
            value=float(params["min_cash_reserve"]),
            step=100.0,
        )
        quad_toggle = sc4.checkbox(
            "Teacher-Approved Quadratic Comparison",
            value=False,
            help="Optional quadratic curve comparison (keep OFF unless approved by teacher).",
        )

        params["extra_shift_hours"] = str(to_decimal(extra_h_in))
        params["extra_shift_hourly_rate"] = str(to_decimal(extra_rate_in))
        params["min_cash_reserve"] = str(to_decimal(reserve_in))

        adv = algebra2_advanced_shift_and_inequalities(
            price=p0,
            requested=requested,
            staff_hours=staff_h,
            hours_per_unit=h_unit,
            revision_hours_per_package=rev_h,
            variable_per_unit=v_total,
            fixed_expense=f_total,
            extra_shift_hours=to_decimal(extra_h_in),
            extra_shift_hourly_rate=to_decimal(extra_rate_in),
            opening_cash=opening_cash,
            min_cash_reserve=to_decimal(reserve_in),
            include_quadratic_demo=quad_toggle,
        )

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Baseline Capacity / Profit", f"{adv['base_capacity']} pkgs | {fmt_usd(adv['base_profit'])}")
        k2.metric(
            "Extra-Shift Capacity / Profit",
            f"{adv['shift_capacity']} pkgs | {fmt_usd(adv['shift_profit'])}",
            delta=f"{fmt_usd(adv['profit_delta'])} vs baseline",
        )
        k3.metric("Added Shift Cost", fmt_usd(adv["added_shift_cost"]))
        k4.metric("Max Feasible Integer Sales", f"{adv['feasible_max_s_int']} pkgs")

        with st.container(border=True):
            st.markdown("**System of Budget, Capacity & Demand Inequalities (Algebra 2 Advanced)**")
            for ineq in adv["inequalities"]:
                st.markdown(f"- `{ineq}`")

        sched_df = pd.DataFrame(adv["schedule_table"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sched_df["s_units"], y=sched_df["revenue"], mode="lines+markers", name="Revenue R(s) ($)", line=dict(width=3)))
        fig.add_trace(go.Scatter(x=sched_df["s_units"], y=sched_df["cost_baseline"], mode="lines", name="Baseline Cost ($)", line=dict(width=2, dash="dash")))
        fig.add_trace(go.Scatter(x=sched_df["s_units"], y=sched_df["cost_extra_shift"], mode="lines", name="Extra-Shift Cost ($)", line=dict(width=2, dash="dot")))
        fig.add_trace(go.Scatter(x=sched_df["s_units"], y=sched_df["profit_extra_shift"], mode="lines+markers", name="Extra-Shift Profit ($)", line=dict(width=3)))
        if quad_toggle and "quadratic_demo_profit" in sched_df.columns:
            fig.add_trace(go.Scatter(x=sched_df["s_units"], y=sched_df["quadratic_demo_profit"], mode="lines", name="Teacher-Approved Quadratic Profit ($)", line=dict(width=2, dash="dashdot")))

        fig.add_hline(y=0, line_width=1.5, line_color="black", annotation_text="Zero Profit Line ($0)")
        fig.add_vrect(
            x0=0,
            x1=adv["feasible_max_s_int"],
            fillcolor="rgba(46, 139, 87, 0.14)",
            line_width=1,
            annotation_text=f"Feasible Region (0 <= s <= {adv['feasible_max_s_int']})",
            annotation_position="top left",
        )
        fig.add_vline(x=adv["base_capacity"], line_dash="dash", annotation_text=f"Base Cap ({adv['base_capacity']})")
        fig.add_vline(x=adv["shift_capacity"], line_dash="dot", annotation_text=f"Shift Cap ({adv['shift_capacity']})")

        fig.update_layout(
            title=(
                f"Advanced Feasible Region & Extra-Shift Sensitivity | {state['team_id']} | "
                f"{state['snapshot_id']} | Actual/Forecast Scenario ({state['simulation_date']})"
            ),
            xaxis_title="Completed Campaign Packages s (units)",
            yaxis_title="Amount (USD $)",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Linked Scenario Data Table (Unit Component Costs Held Fixed at $80.00/pkg)**")
        st.dataframe(sched_df, use_container_width=True)

        export_meta = (
            f"# Team: {state['team_id']} | Course: {state['course']} ({state['selected_level']}) | "
            f"Snapshot: {state['snapshot_id']} | Date: {state['simulation_date']} | Label: Projected Scenario\n"
        )
        st.download_button(
            "Download Graph Data Table + Assumptions (CSV)",
            data=export_meta + sched_df.to_csv(index=False),
            file_name=f"mkt1_advanced_shift_{state['snapshot_id']}.csv",
            mime="text/csv",
        )

        st.markdown("**Required Student Interpretation Prompts**")
        for q in adv["interpretation_questions"]:
            st.warning(q)


def render_ledger_and_persistence_page(state: Dict[str, Any]) -> None:
    st.header("Dated Event Ledger & Durable Save/Load JSON")
    st.caption(
        "Handbook Rule (pp. 9, 58): Browser session state is ephemeral on Render/refresh. "
        "Export your Snapshot JSON after every approved round and restore it when resuming."
    )

    c_exp, c_imp = st.columns(2)
    with c_exp:
        st.subheader("Export Approved Snapshot JSON")
        snap_str = export_snapshot_json(state)
        st.download_button(
            label=f"Download {state['snapshot_id']}.json",
            data=snap_str,
            file_name=f"{state['team_id'].replace(' ', '_')}_{state['snapshot_id']}.json",
            mime="application/json",
            type="primary",
        )
        with st.expander("Preview Snapshot JSON"):
            st.code(snap_str, language="json")

    with c_imp:
        st.subheader("Restore / Import Snapshot JSON")
        uploaded = st.file_uploader("Upload saved Snapshot JSON", type=["json"], key="snapshot_uploader")
        if uploaded is not None:
            raw_text = uploaded.read().decode("utf-8")
            if st.button("Validate & Restore Uploaded Snapshot", key="restore_btn"):
                ok, msg, restored = validate_and_load_snapshot_json(raw_text, state)
                if ok and restored is not None:
                    st.session_state["cvl_state"] = restored
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.divider()
    st.subheader("Dated Event Ledger & Time-Horizon Aggregation")
    if not state["ledger"]:
        st.info("No transactions committed yet. Commit a month in Normal Mode or run Fixture-Test Mode to populate the ledger.")
        return

    views = aggregate_ledger_views(state["ledger"], working_days=state["working_days"])
    tab_raw, tab_m, tab_d, tab_y = st.tabs(
        ["Raw Event Ledger", "Monthly View", "Daily Modeled Allocation", "Yearly Aggregation"]
    )
    with tab_raw:
        raw_df = pd.DataFrame(state["ledger"])
        st.dataframe(raw_df, use_container_width=True)
        st.download_button(
            "Download Raw Ledger CSV",
            data=raw_df.to_csv(index=False),
            file_name=f"ledger_{state['snapshot_id']}.csv",
            mime="text/csv",
        )
    with tab_m:
        st.dataframe(views["monthly"], use_container_width=True)
    with tab_d:
        st.caption(
            f"Daily figures divide monthly totals by working_days = {state['working_days']} "
            "(explicitly labeled as modeled allocations, never monthly / 30)."
        )
        st.dataframe(views["daily"], use_container_width=True)
    with tab_y:
        st.dataframe(views["yearly"], use_container_width=True)


def render_acceptance_tests_page() -> None:
    st.header("Stage 1 Acceptance & Fixture Verification Suite")
    st.caption(
        "Runs deterministic checks from Handbook pp. 60, 68, and 100 in an isolated sandbox without altering your active business ledger."
    )

    if st.button("Run All Stage 1 Acceptance Checks Now", type="primary"):
        checks = []

        _, rep = replay_fixture_rows(create_initial_state(), FIXTURE_ROWS)
        f_ok = (
            rep[0]["sold"] == 10 and rep[0]["revenue"] == Decimal("2500.00") and rep[0]["total_expense"] == Decimal("1700.00")
            and rep[0]["profit"] == Decimal("800.00") and rep[0]["closing_cash"] == Decimal("4800.00")
            and rep[1]["sold"] == 10 and rep[1]["revenue"] == Decimal("2500.00") and rep[1]["total_expense"] == Decimal("1800.00")
            and rep[1]["profit"] == Decimal("700.00") and rep[1]["closing_cash"] == Decimal("5500.00")
            and rep[2]["sold"] == 7 and rep[2]["revenue"] == Decimal("1750.00") and rep[2]["total_expense"] == Decimal("1460.00")
            and rep[2]["profit"] == Decimal("290.00") and rep[2]["closing_cash"] == Decimal("5790.00")
        )
        checks.append(("MKT-1 3-Month Fixture Replay (Jan/Feb/Mar)", "PASS" if f_ok else "FAIL", "Closing cash: $4,800 -> $5,500 -> $5,790"))

        rev_test = calculate_monthly_metrics(
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
        r_ok = (
            rev_test["capacity"] == 8
            and rev_test["variable_per_unit"] == Decimal("90.00")
            and rev_test["net_revenue"] == Decimal("2000.00")
            and rev_test["variable_expense"] == Decimal("720.00")
            and rev_test["operating_profit"] == Decimal("380.00")
        )
        checks.append(("MKT-1 Extra Revisions (+2 hrs/pkg)", "PASS" if r_ok else "FAIL", "Capacity=8, Unit=$90, Rev=$2,000, Var=$720, Profit=$380"))

        zero_test = calculate_monthly_metrics(
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
        z_ok = (
            zero_test["net_revenue"] == Decimal("0.00")
            and zero_test["variable_expense"] == Decimal("0.00")
            and zero_test["operating_profit"] == Decimal("-900.00")
        )
        checks.append(("Zero Sales & Division-by-Zero Safety", "PASS" if z_ok else "FAIL", "Rev=$0.00, Var=$0.00, Profit=-$900.00"))

        loan_test = calculate_monthly_metrics(
            opening_cash=Decimal("4000.00"),
            price=Decimal("250.00"),
            requested=0,
            staff_hours=Decimal("80.00"),
            hours_per_unit=Decimal("8.00"),
            revision_hours_per_package=Decimal("0.00"),
            extra_revision_hourly_cost=Decimal("5.00"),
            variable_costs=DEFAULT_VARIABLE_COSTS,
            fixed_costs=DEFAULT_FIXED_COSTS,
            loan_cash_received=Decimal("2000.00"),
        )
        l_ok = loan_test["net_revenue"] == Decimal("0.00") and loan_test["ending_cash"] == Decimal("5100.00")
        checks.append(("Loan Proceeds Accounting Rule", "PASS" if l_ok else "FAIL", "Revenue unchanged ($0); Cash +$2,000 before fixed expense"))

        s_dup = create_initial_state()
        ok1, _ = commit_simulation_step(s_dup, "RUN-TEST-1", "2027-01-31", zero_test, "Normal Mode")
        ok2, _ = commit_simulation_step(s_dup, "RUN-TEST-1", "2027-01-31", zero_test, "Normal Mode")
        checks.append(("Duplicate Run ID Protection", "PASS" if (ok1 and not ok2) else "FAIL", "Second commit with same run_id rejected"))

        s_v2 = create_initial_state()
        commit_simulation_step(s_v2, "RUN-V1", "2027-01-31", zero_test, "Normal Mode")
        stale_json = export_snapshot_json(create_initial_state())
        ok_stale, _msg_stale, _ = validate_and_load_snapshot_json(stale_json, s_v2)

        wrong_team_data = json.loads(stale_json)
        wrong_team_data["team_id"] = "Other Team"
        ok_team, _msg_team, _ = validate_and_load_snapshot_json(json.dumps(wrong_team_data), create_initial_state())
        checks.append(("Stale Version & Foreign Team Rejection", "PASS" if (not ok_stale and not ok_team) else "FAIL", "v1 rejected against v2; wrong team_id rejected"))

        f_no_be = algebra2_foundation_analysis(Decimal("80.00"), Decimal("80.00"), Decimal("900.00"), 10)
        app_chk = algebra2_applied_analysis(Decimal("250.00"), 12, Decimal("80.00"), Decimal("900.00"), 10)
        a2_ok = (f_no_be["exact_break_even"] is None) and (app_chk["demand_at_p0"] == 12.0)
        checks.append(("Algebra 2 Course Acceptance Checks", "PASS" if a2_ok else "FAIL", "p0=v -> no positive break-even; q(p0)=D0=12"))

        res_df = pd.DataFrame(checks, columns=["Test Case", "Status", "Verification Evidence"])
        st.dataframe(res_df, use_container_width=True)


def render_placeholder_stage(title: str, stage_label: str, description: str) -> None:
    st.header(title)
    st.warning(f"**UNIMPLEMENTED PLACEHOLDER ({stage_label}):** {description}")
    st.info(
        "Per Student Handbook p. 102, Stage 1 (inputs, deterministic math, ledger, save/restore, and fixture tests) "
        "must pass verification and a two-report Decision Memo before building Stage 2 or Stage 3 modules."
    )


def main() -> None:
    if st is None:
        raise RuntimeError("Streamlit is required to run the web UI. Install dependencies via `pip install -r requirements.txt`.")
    st.set_page_config(
        page_title="Career Venture Lab — Team Lucas (MKT-1)",
        layout="wide",
    )
    init_session()
    state = st.session_state["cvl_state"]

    st.sidebar.title("Career Venture Lab")
    st.sidebar.markdown(
        f"**Team:** `{state['team_id']}`  \n"
        f"**Pathway:** `{state['pathway_id']}` (Marketing Agency)  \n"
        f"**Course:** `{state['course']}` (`{state['selected_level']}`)  \n"
        f"**Snapshot:** `{state['snapshot_id']}` (v{state['state_version']})"
    )

    nav = st.sidebar.radio(
        "Navigation (Staged Build)",
        options=[
            "Overview (Stage 1)",
            "Inputs & Funding (Stage 1)",
            "Math Skills & Visuals (Stage 1)",
            "Ledger & Save/Load JSON (Stage 1)",
            "Acceptance Tests (Stage 1)",
            "Operations & Finance Reports [Stage 2 - Unimplemented]",
            "AI Recommendations [Stage 2 - Unimplemented]",
            "Marketing Studio [Stage 2 - Unimplemented]",
            "Cross-Course & Decisions [Stage 3 - Unimplemented]",
            "Assessment Panel [Stage 3 - Unimplemented]",
            "Optional Storefront [Stage 4 - Lowest Priority]",
        ],
    )

    if nav == "Overview (Stage 1)":
        render_overview_page(state)
    elif nav == "Inputs & Funding (Stage 1)":
        render_inputs_and_funding_page(state)
    elif nav == "Math Skills & Visuals (Stage 1)":
        render_algebra2_page(state)
    elif nav == "Ledger & Save/Load JSON (Stage 1)":
        render_ledger_and_persistence_page(state)
    elif nav == "Acceptance Tests (Stage 1)":
        render_acceptance_tests_page()
    elif "Operations & Finance" in nav:
        render_placeholder_stage(
            "Operations & Finance Reports",
            "Stage 2",
            "Full Report Center (Income Statement, Cash-Flow, Budget Variance, Balance Sheet, PDF/CSV exports) will be built in Stage 2 after Stage 1 fixture sign-off.",
        )
    elif "AI Recommendations" in nav:
        render_placeholder_stage(
            "AI Recommendations (Manual Handoff)",
            "Stage 2",
            "Structured recommendation import/review cards for Finance, Operations, Market/Marketing, and Independent Reviewer Gems/Skills are staged for Stage 2. No fake AI responses are simulated here.",
        )
    elif "Marketing Studio" in nav:
        render_placeholder_stage(
            "Costed Marketing Studio",
            "Stage 2",
            "Draft flyer/social/email builder with itemized design, print, asset, and placement costs and duplicate campaign_id protection is scheduled for Stage 2.",
        )
    elif "Cross-Course" in nav:
        render_placeholder_stage(
            "Cross-Course Connections & Decision Memos",
            "Stage 3",
            "Two-subject cross-course evidence panel and formal two-report Decision Memo workflow are scheduled for Stage 3.",
        )
    elif "Assessment Panel" in nav:
        render_placeholder_stage(
            "Snapshot-Based Assessment Panel",
            "Stage 3",
            "Frozen-snapshot practice questions and teacher-controlled LMS/server-authenticated graded keys are scheduled for Stage 3.",
        )
    else:
        render_placeholder_stage(
            "Optional Demonstration Storefront",
            "Stage 4 — Lowest Priority",
            "Fictional test checkout storefront (DEMONSTRATION BUSINESS — NO REAL PURCHASES) is built last only after all core Stage 1-3 requirements pass.",
        )


if __name__ == "__main__":
    main()
