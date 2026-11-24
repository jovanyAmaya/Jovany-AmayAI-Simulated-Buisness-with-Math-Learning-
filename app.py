import hashlib
import io
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from fpdf import FPDF

PROGRESSION = "FIN"
FIXTURE_PATH = Path("sample_data/monthly_fixture.csv")
EXPERIMENT_PATH = Path("sample_data/experiment.csv")


def get_default_state() -> dict:
    """Return default simulator parameters configured for the FIN progression."""
    return {
        "progression": PROGRESSION,
        "months": 12,
        "starting_cash": 150000.0,
        "base_demand": 400.0,
        "monthly_growth_rate": 0.06,
        "unit_price": 120.0,
        "unit_cogs": 36.0,
        "monthly_opex": 28000.0,
        "max_capacity": 850.0,
        "annual_discount_rate": 0.10,
    }


def build_run_signature(params: dict) -> str:
    """Create a deterministic hash of run parameters for duplicate-run protection."""
    serialized = json.dumps(params, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def run_deterministic_model(params: dict) -> tuple[pd.DataFrame, dict]:
    """Compute monthly financial ledger, capacity caps, NPV, and runway for FIN."""
    months = int(params["months"])
    cash = float(params["starting_cash"])
    base_demand = float(params["base_demand"])
    growth = float(params["monthly_growth_rate"])
    price = float(params["unit_price"])
    unit_cogs = float(params["unit_cogs"])
    opex = float(params["monthly_opex"])
    cap = float(params["max_capacity"])
    discount_annual = float(params["annual_discount_rate"])

    dates = pd.date_range("2026-01-31", periods=months, freq="ME")
    rows = []
    cash_flows = [-cash]
    runway_month = None

    for idx in range(months):
        month_num = idx + 1
        unconstrained_demand = base_demand * ((1.0 + growth) ** idx)
        units_sold = min(unconstrained_demand, cap)
        revenue = units_sold * price
        cogs = units_sold * unit_cogs
        gross_profit = revenue - cogs
        net_cash_flow = gross_profit - opex
        cash += net_cash_flow
        cash_flows.append(net_cash_flow)

        if cash <= 0 and runway_month is None:
            runway_month = month_num

        rows.append(
            {
                "date": dates[idx].strftime("%Y-%m-%d"),
                "month": month_num,
                "progression": params.get("progression", PROGRESSION),
                "unconstrained_demand": round(unconstrained_demand, 2),
                "units_sold": round(units_sold, 2),
                "capacity_cap": round(cap, 2),
                "revenue": round(revenue, 2),
                "cogs": round(cogs, 2),
                "gross_profit": round(gross_profit, 2),
                "opex": round(opex, 2),
                "net_cash_flow": round(net_cash_flow, 2),
                "ending_cash": round(cash, 2),
            }
        )

    df = pd.DataFrame(rows)
    monthly_rate = (1.0 + discount_annual) ** (1.0 / 12.0) - 1.0
    discount_factors = np.array([(1.0 + monthly_rate) ** t for t in range(len(cash_flows))])
    npv = float(np.sum(np.array(cash_flows) / discount_factors))

    total_rev = float(df["revenue"].sum())
    total_gp = float(df["gross_profit"].sum())
    gross_margin_pct = (total_gp / total_rev * 100.0) if total_rev > 0 else 0.0

    summary = {
        "progression": params.get("progression", PROGRESSION),
        "total_revenue": round(total_rev, 2),
        "gross_margin_pct": round(gross_margin_pct, 2),
        "ending_cash": round(cash, 2),
        "npv": round(npv, 2),
        "runway_months": runway_month if runway_month is not None else f">{months}",
        "capacity_capped": bool((df["unconstrained_demand"] > cap).any()),
    }
    return df, summary


def run_reproducible_experiment(params: dict, volatility: float, trials: int, seed: int) -> pd.DataFrame:
    """Run a reproducible RNG experiment using numpy default_rng for FIN cash-flow risk."""
    rng = np.random.default_rng(int(seed))
    months = int(params["months"])
    shocks = rng.normal(loc=float(params["monthly_growth_rate"]), scale=float(volatility), size=(int(trials), months))

    cash_paths = np.zeros((int(trials), months))
    current_cash = np.full(int(trials), float(params["starting_cash"]))
    current_demand = np.full(int(trials), float(params["base_demand"]))

    unit_margin = float(params["unit_price"]) - float(params["unit_cogs"])
    cap = float(params["max_capacity"])
    opex = float(params["monthly_opex"])

    for m in range(months):
        if m > 0:
            current_demand = np.maximum(0.0, current_demand * (1.0 + shocks[:, m]))
        sold = np.minimum(current_demand, cap)
        net_cf = (sold * unit_margin) - opex
        current_cash = current_cash + net_cf
        cash_paths[:, m] = current_cash

    return pd.DataFrame(
        {
            "month": np.arange(1, months + 1),
            "p10_ending_cash": np.percentile(cash_paths, 10, axis=0),
            "p50_ending_cash": np.percentile(cash_paths, 50, axis=0),
            "p90_ending_cash": np.percentile(cash_paths, 90, axis=0),
        }
    )


def render_matplotlib_png(df: pd.DataFrame) -> bytes:
    """Render static PNG chart for download."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["month"], df["revenue"], label="Revenue ($)", linewidth=2)
    ax.plot(df["month"], df["net_cash_flow"], label="Net Cash Flow ($)", linewidth=2)
    ax.axhline(0, color="gray", linestyle="--", linewidth=1)
    ax.set_title(f"{PROGRESSION} Progression — Revenue & Net Cash Flow")
    ax.set_xlabel("Month")
    ax.set_ylabel("USD ($)")
    ax.legend()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()


def generate_pdf_brief(summary: dict, df: pd.DataFrame) -> bytes:
    """Generate printable PDF report for the Report Center using fpdf2."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Business & Financial Simulator Brief ({summary['progression']})", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.ln(3)
    for key, value in summary.items():
        pdf.cell(0, 8, f"{key.replace('_', ' ').title()}: {value}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Monthly Ledger Snapshot", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)

    for _, row in df.iterrows():
        line = (
            f"{row['date']} | Units: {row['units_sold']:.0f}/{row['capacity_cap']:.0f} | "
            f"Rev: ${row['revenue']:,.2f} | Net CF: ${row['net_cash_flow']:,.2f} | Cash: ${row['ending_cash']:,.2f}"
        )
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


def export_state_json(params: dict) -> str:
    return json.dumps(params, indent=2, sort_keys=True)


def import_state_json(raw_json: str) -> dict:
    loaded = json.loads(raw_json)
    if not isinstance(loaded, dict):
        raise ValueError("State JSON must be an object.")
    merged = get_default_state()
    merged.update(loaded)
    return merged


def main() -> None:
    st.set_page_config(page_title="FIN Simulator", layout="wide")

    if "params" not in st.session_state:
        st.session_state.params = get_default_state()
    if "experiment_cache" not in st.session_state:
        st.session_state.experiment_cache = {}

    st.title(f"Business & Financial Simulator — Progression: {st.session_state.params['progression']}")

    with st.sidebar:
        st.header("FIN Progression Controls")
        progression = st.selectbox("Progression Pathway", ["FIN"], index=0)
        months = st.slider("Horizon (Months)", 6, 36, int(st.session_state.params["months"]))
        starting_cash = st.number_input("Starting Cash ($)", min_value=0.0, value=float(st.session_state.params["starting_cash"]), step=5000.0)
        base_demand = st.number_input("Initial Monthly Demand (Units)", min_value=0.0, value=float(st.session_state.params["base_demand"]), step=25.0)
        growth_rate = st.slider("Monthly Demand Growth (%)", -10.0, 25.0, float(st.session_state.params["monthly_growth_rate"]) * 100.0, 0.5) / 100.0
        unit_price = st.number_input("Unit Price ($)", min_value=0.0, value=float(st.session_state.params["unit_price"]), step=5.0)
        unit_cogs = st.number_input("Unit COGS ($)", min_value=0.0, value=float(st.session_state.params["unit_cogs"]), step=2.0)
        monthly_opex = st.number_input("Monthly Fixed OpEx ($)", min_value=0.0, value=float(st.session_state.params["monthly_opex"]), step=1000.0)
        max_capacity = st.number_input("Monthly Capacity Ceiling (Units)", min_value=0.0, value=float(st.session_state.params["max_capacity"]), step=25.0)
        discount_rate = st.slider("Annual Discount Rate / WACC (%)", 0.0, 30.0, float(st.session_state.params["annual_discount_rate"]) * 100.0, 0.5) / 100.0

        st.session_state.params = {
            "progression": progression,
            "months": months,
            "starting_cash": starting_cash,
            "base_demand": base_demand,
            "monthly_growth_rate": growth_rate,
            "unit_price": unit_price,
            "unit_cogs": unit_cogs,
            "monthly_opex": monthly_opex,
            "max_capacity": max_capacity,
            "annual_discount_rate": discount_rate,
        }

    df_ledger, summary = run_deterministic_model(st.session_state.params)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["FIN Dashboard & Curves", "Event Ledger & Fixtures", "RNG Experiment Studio", "Report Center & JSON State"]
    )

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ending Cash", f"${summary['ending_cash']:,.2f}")
        c2.metric("Net Present Value (NPV)", f"${summary['npv']:,.2f}")
        c3.metric("Gross Margin", f"{summary['gross_margin_pct']:.1f}%")
        c4.metric("Cash Runway", f"{summary['runway_months']} mos")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_ledger["date"], y=df_ledger["revenue"], name="Revenue ($)", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=df_ledger["date"], y=df_ledger["net_cash_flow"], name="Net Cash Flow ($)", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=df_ledger["date"], y=df_ledger["ending_cash"], name="Ending Cash ($)", mode="lines"))
        fig.update_layout(title="Linked Revenue, Cash Flow & Treasury Curve", xaxis_title="Date", yaxis_title="USD ($)")
        st.plotly_chart(fig, use_container_width=True)

        cap_fig = go.Figure()
        cap_fig.add_trace(go.Scatter(x=df_ledger["date"], y=df_ledger["unconstrained_demand"], name="Unconstrained Demand"))
        cap_fig.add_trace(go.Scatter(x=df_ledger["date"], y=df_ledger["units_sold"], name="Actual Units Sold"))
        cap_fig.add_trace(
            go.Scatter(x=df_ledger["date"], y=df_ledger["capacity_cap"], name="Capacity Asymptote", line=dict(dash="dash"))
        )
        cap_fig.update_layout(title="Demand vs. Capacity Ceiling", xaxis_title="Date", yaxis_title="Units")
        st.plotly_chart(cap_fig, use_container_width=True)

        st.download_button(
            "Download Chart PNG",
            data=render_matplotlib_png(df_ledger),
            file_name="fin_projection_chart.png",
            mime="image/png",
        )

    with tab2:
        st.subheader("Simulated Dated Event Ledger")
        st.dataframe(df_ledger, use_container_width=True)
        st.download_button(
            "Export Ledger CSV",
            data=df_ledger.to_csv(index=False).encode("utf-8"),
            file_name="fin_simulated_ledger.csv",
            mime="text/csv",
        )

        st.subheader("Sample Data: monthly_fixture.csv")
        if FIXTURE_PATH.exists():
            st.dataframe(pd.read_csv(FIXTURE_PATH), use_container_width=True)

        st.subheader("Sample Data: experiment.csv")
        if EXPERIMENT_PATH.exists():
            st.dataframe(pd.read_csv(EXPERIMENT_PATH), use_container_width=True)

    with tab3:
        col1, col2, col3 = st.columns(3)
        volatility = col1.slider("Growth Volatility (%)", 0.5, 15.0, 3.0, 0.5) / 100.0
        trials = col2.selectbox("Simulation Trials", [200, 500, 1000], index=1)
        seed = col3.number_input("RNG Seed", min_value=1, value=42, step=1)

        exp_params = {**st.session_state.params, "volatility": volatility, "trials": trials, "seed": int(seed)}
        sig = build_run_signature(exp_params)

        if st.button("Run Experiment"):
            if sig in st.session_state.experiment_cache:
                st.info(f"Duplicate run prevented — loaded cached experiment `{sig}`.")
            else:
                st.session_state.experiment_cache[sig] = run_reproducible_experiment(
                    st.session_state.params, volatility=volatility, trials=trials, seed=int(seed)
                )

        if sig in st.session_state.experiment_cache:
            exp_res = st.session_state.experiment_cache[sig]
            exp_fig = go.Figure()
            exp_fig.add_trace(go.Scatter(x=exp_res["month"], y=exp_res["p90_ending_cash"], name="P90 Cash", line=dict(dash="dot")))
            exp_fig.add_trace(go.Scatter(x=exp_res["month"], y=exp_res["p50_ending_cash"], name="P50 Median Cash", mode="lines+markers"))
            exp_fig.add_trace(go.Scatter(x=exp_res["month"], y=exp_res["p10_ending_cash"], name="P10 Cash", line=dict(dash="dot")))
            exp_fig.update_layout(title="FIN Cash-Flow Confidence Fan Chart", xaxis_title="Month", yaxis_title="Ending Cash ($)")
            st.plotly_chart(exp_fig, use_container_width=True)

    with tab4:
        st.download_button(
            "Download FIN Report PDF",
            data=generate_pdf_brief(summary, df_ledger),
            file_name="fin_report_brief.pdf",
            mime="application/pdf",
        )

        st.subheader("Save / Restore Scenario JSON")
        state_str = export_state_json(st.session_state.params)
        st.download_button(
            "Download State JSON",
            data=state_str.encode("utf-8"),
            file_name="fin_state.json",
            mime="application/json",
        )
        uploaded_json = st.file_uploader("Restore State JSON", type=["json"])
        if uploaded_json is not None:
            st.session_state.params = import_state_json(uploaded_json.read().decode("utf-8"))
            st.success("FIN state restored.")


if __name__ == "__main__":
    main()