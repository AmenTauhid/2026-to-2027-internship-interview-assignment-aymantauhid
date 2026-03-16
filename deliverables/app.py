"""
Government of Canada Contracts - Analysis Dashboard
Author: Ayman Tauhid
"""

import os
import streamlit as st
import duckdb
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv

load_dotenv(override=True)
CSV_PATH = os.getenv("LOCAL_DATASET_PATH", "data/contracts.csv")

# Color palette
BLUE = "#4878A8"
RED = "#D04040"
ORANGE = "#E8A040"
GREEN = "#6BAF6B"
GRAY = "#888888"

st.set_page_config(page_title="Contract Analysis", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
st.markdown("""
<style>
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
    [data-testid="stMetricLabel"] {font-size: 0.9rem; color: #555;}
    .insight-box {
        background: #f0f4f8; border-left: 4px solid #4878A8;
        padding: 1rem 1.2rem; margin: 1rem 0; border-radius: 0 6px 6px 0;
    }
    .finding-box {
        background: #fdf0f0; border-left: 4px solid #D04040;
        padding: 1rem 1.2rem; margin: 1rem 0; border-radius: 0 6px 6px 0;
    }
    .action-box {
        background: #f0fdf0; border-left: 4px solid #6BAF6B;
        padding: 1rem 1.2rem; margin: 1rem 0; border-radius: 0 6px 6px 0;
    }
    div[data-testid="stHorizontalBlock"] > div {padding: 0 0.3rem;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading 1.26M contract records...")
def load_data(csv_path: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"""
        CREATE TABLE raw AS
        SELECT * FROM read_csv_auto('{csv_path}', all_varchar=true, strict_mode=false, parallel=false)
    """)
    con.execute("""
        CREATE VIEW contracts AS
        SELECT *,
            LEFT(reporting_period, 9) AS fiscal_year,
            RIGHT(reporting_period, 2) AS quarter,
            TRY_CAST(contract_value AS DOUBLE) AS cv,
            TRY_CAST(original_value AS DOUBLE) AS ov,
            TRY_CAST(amendment_value AS DOUBLE) AS av,
            SPLIT_PART(owner_org_title, ' | ', 1) AS department,
            CASE
                WHEN reporting_period < '2019-2020' THEN 'Pre-2019'
                WHEN reporting_period >= '2019-2020' AND reporting_period < '2022-2023' THEN '2019-2022'
                ELSE 'Post-2022'
            END AS era
        FROM raw
        WHERE reporting_period LIKE '____-____-Q_'
          AND owner_org_title NOT LIKE 'National Defence%'
    """)
    return con

def q(sql): return load_data(CSV_PATH).execute(sql)
def fetch_df(sql): return q(sql).fetchdf()
def fetch_one(sql): return q(sql).fetchone()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("Contract Analysis")
    st.caption("Government of Canada\nContracts over $10,000")

    st.markdown("---")
    st.subheader("Filters")

    # Department filter
    dept_list = fetch_df("SELECT DISTINCT department FROM contracts ORDER BY department")
    dept_options = ["All Departments"] + dept_list["department"].tolist()
    selected_dept = st.selectbox("Department", dept_options,
        help="Filter all charts and metrics to a single department.")

    # Commodity filter
    selected_commodity = st.selectbox("Commodity Type", ["All", "Services", "Goods", "Construction"],
        help="commodity_type not mandatory before 2019. Pre-2019 breakdown is incomplete.")

    st.markdown("---")
    with st.expander("Data Quality & Limitations", expanded=False):
        st.markdown("**Data completeness**")
        st.markdown(
            "- **Pre-2019**: Voluntary reporting. `commodity_type`, `instrument_type` not mandatory.\n"
            "- **Post-2019**: Mandatory reporting. Core fields reliable.\n"
        )
        st.markdown("**Assumptions**")
        st.markdown(
            "- National Defence excluded\n"
            "- `contract_value` on amendments = cumulative total, not incremental\n"
            "- Vendor names used as-is (no normalization)\n"
            "- All values nominal CAD, not inflation-adjusted"
        )
        st.markdown("**Data issues**")
        malformed = fetch_one("SELECT COUNT(*) FROM raw WHERE reporting_period IS NOT NULL AND reporting_period NOT LIKE '____-____-Q_' AND owner_org_title NOT LIKE 'National Defence%'")[0]
        st.markdown(
            f"- **{malformed:,}** malformed `reporting_period` values excluded\n"
            "- Vendor name inconsistency (10+ variants for some vendors)\n"
            "- `reporting_period` = reporting date, not award date\n"
            "- 28% of rows have no `instrument_type` (pre-mandatory)\n"
            "- Zero cast failures on financial fields"
        )

    st.markdown("---")
    st.caption("Built with DuckDB, Plotly, Streamlit")
    st.caption("Analysis by Ayman Tauhid")

# ---------------------------------------------------------------------------
# Filters & Scopes
# ---------------------------------------------------------------------------

COMMODITY_MAP = {"Services": "S", "Goods": "G", "Construction": "C"}

def build_filter():
    parts = []
    if selected_dept != "All Departments":
        safe_dept = selected_dept.replace("'", "''")
        parts.append(f"department = '{safe_dept}'")
    if selected_commodity != "All":
        parts.append(f"commodity_type = '{COMMODITY_MAP[selected_commodity]}'")
    return " AND ".join(parts) if parts else "1=1"

cf = build_filter()
commodity_label = selected_commodity if selected_commodity != "All" else "All commodities"
dept_label = selected_dept if selected_dept != "All Departments" else "All departments"
filter_label = f"{commodity_label}, {dept_label}"

SCOPES = [
    ("Pre-2019 (voluntary)",  f"{cf} AND era = 'Pre-2019'"),
    ("Post-2019 (mandatory)", f"{cf} AND era IN ('2019-2022', 'Post-2022')"),
    ("All Years",             f"{cf}"),
]
SCOPE_NAMES = [s[0] for s in SCOPES]

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("A self-reinforcing cycle in federal procurement")
st.markdown(
    "- Year-end budget pressure leads to rushed contracts\n"
    "- Those contracts grow through amendments\n"
    "- A small group of vendors benefits disproportionately, reinforcing the cycle\n\n"
    "**1.26M rows of Government of Canada procurement data (excl. National Defence) reveal the pattern.**"
)

# ---------------------------------------------------------------------------
# Overview metrics
# ---------------------------------------------------------------------------

row_total = fetch_one(f"SELECT COUNT(*) FROM contracts WHERE {cf}")[0]
total_value = fetch_one(f"SELECT SUM(cv) FROM contracts WHERE {cf}")[0] or 0
unique_vendors = fetch_one(f"SELECT COUNT(DISTINCT vendor_name) FROM contracts WHERE {cf}")[0]
contracts_only = fetch_one(f"SELECT COUNT(*) FROM contracts WHERE {cf} AND instrument_type='C'")[0]
amendments_only = fetch_one(f"SELECT COUNT(*) FROM contracts WHERE {cf} AND instrument_type='A'")[0]

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Rows", f"{row_total:,.0f}")
c2.metric("Contracts", f"{contracts_only:,.0f}")
c3.metric("Amendments", f"{amendments_only:,.0f}")
c4.metric("Total Value", f"${total_value/1e9:,.1f}B")
c5.metric("Vendors", f"{unique_vendors:,.0f}")
c6.metric("Amendment Rate", f"{amendments_only*100/row_total:.1f}%")

st.markdown("---")

# ===================================================================
# TABBED INSIGHTS
# ===================================================================

tab1, tab2, tab3, tab5 = st.tabs([
    "Insight 1: Q4 Spending Surge",
    "Insight 2: Amendment Growth",
    "Insight 3: Vendor Concentration",
    "Next Steps",
])

# ===================================================================
# INSIGHT 1: Q4 Spending Surge
# ===================================================================

with tab1:
    st.header("Fiscal year-end spending surge")

    # Headline metrics for this insight
    q4_row = fetch_one(f"""
        SELECT ROUND(AVG(CASE WHEN quarter='Q4' THEN cv END) /
            NULLIF(AVG(CASE WHEN quarter!='Q4' THEN cv END), 0), 2) AS multiplier,
            ROUND(SUM(CASE WHEN quarter='Q4' THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS q4_share
        FROM contracts WHERE {cf} AND era IN ('2019-2022','Post-2022') AND instrument_type='C'
    """)
    m1, m2, m3 = st.columns(3)
    m1.metric("Q4 Value Multiplier (post-2019)", f"{q4_row[0]:.2f}x" if q4_row[0] else "N/A")
    m2.metric("Q4 Share of Contracts (post-2019)", f"{q4_row[1]:.1f}%" if q4_row[1] else "N/A")
    sole_src = fetch_one(f"""
        SELECT ROUND(SUM(CASE WHEN quarter='Q4' AND solicitation_procedure='TN' THEN 1 ELSE 0 END)*100.0 /
            NULLIF(SUM(CASE WHEN quarter='Q4' THEN 1 ELSE 0 END), 0), 1)
        FROM contracts WHERE {cf} AND era IN ('2019-2022','Post-2022') AND instrument_type='C'
    """)
    m3.metric("Q4 Sole-Source Rate (post-2019)", f"{sole_src[0]:.1f}%" if sole_src[0] else "N/A")

    st.markdown('<div class="insight-box">'
        "- Canada's fiscal year ends March 31<br>"
        "- Q4 (Jan-Mar) is the final quarter before budgets reset<br>"
        "- If departments rush to spend, Q4 should show more contracts and higher values"
        '</div>', unsafe_allow_html=True)

    # Row 1: Q4 avg contract value by scope
    fig_avg = make_subplots(rows=1, cols=3, subplot_titles=SCOPE_NAMES, shared_yaxes=True)
    for i, (scope_name, scope_filter) in enumerate(SCOPES):
        qtr = fetch_df(f"""
            SELECT quarter, ROUND(AVG(cv), 0) AS avg_val
            FROM contracts WHERE {scope_filter} AND instrument_type='C'
            GROUP BY quarter ORDER BY quarter
        """)
        if not qtr.empty:
            colors = [BLUE if q != "Q4" else RED for q in qtr["quarter"]]
            fig_avg.add_trace(go.Bar(x=qtr["quarter"], y=qtr["avg_val"], marker_color=colors,
                text=[f"${v/1000:.0f}K" for v in qtr["avg_val"]], textposition="outside", cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Avg: $%{y:,.0f}<extra></extra>", showlegend=False), row=1, col=i+1)
    fig_avg.update_layout(height=420, template="plotly_white",
        title="Q4 avg contract value - new contracts only", margin=dict(t=60, b=10))
    fig_avg.update_yaxes(rangemode="tozero", title_text="Avg contract value ($)", row=1, col=1)
    st.plotly_chart(fig_avg, use_container_width=True)
    st.caption("Q4 (red) shows a clear value premium post-2019. Pre-2019 data is voluntary and less reliable.")

    # Row 2: Q4 share by transaction type by scope
    fig_share = make_subplots(rows=1, cols=3, subplot_titles=SCOPE_NAMES, shared_yaxes=True)
    for i, (scope_name, scope_filter) in enumerate(SCOPES):
        inst = fetch_df(f"""
            SELECT CASE instrument_type WHEN 'C' THEN 'New Contracts' WHEN 'A' THEN 'Amendments'
                WHEN 'SOSA' THEN 'Standing Offers' END AS type,
                ROUND(SUM(CASE WHEN quarter='Q4' THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS q4_pct
            FROM contracts WHERE {scope_filter} AND instrument_type IN ('A','C','SOSA')
            GROUP BY instrument_type ORDER BY q4_pct DESC
        """)
        if not inst.empty:
            fig_share.add_trace(go.Bar(x=inst["type"], y=inst["q4_pct"],
                marker_color=[RED if p > 30 else ORANGE if p > 25 else BLUE for p in inst["q4_pct"]],
                text=[f"{v}%" for v in inst["q4_pct"]], textposition="outside", cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Q4 share: %{y:.1f}%<extra></extra>", showlegend=False), row=1, col=i+1)
    fig_share.add_hline(y=25, line_dash="dash", line_color=GRAY, annotation_text="Expected 25%")
    fig_share.update_layout(height=400, template="plotly_white",
        title="Q4 share by transaction type", margin=dict(t=60))
    fig_share.update_yaxes(title_text="% in Q4", row=1, col=1)
    st.plotly_chart(fig_share, use_container_width=True)
    st.caption("Dashed line = expected 25% if spending were even. Amendments are consistently more concentrated in Q4 than new contracts.")

    # Row 3: Top departments by Q4 value multiplier by scope
    if selected_dept == "All Departments":
        fig_dept = make_subplots(rows=1, cols=3, subplot_titles=SCOPE_NAMES, shared_yaxes=True)
        for i, (scope_name, scope_filter) in enumerate(SCOPES):
            dept = fetch_df(f"""
                SELECT LEFT(department, 20) AS dept_name,
                    ROUND(AVG(CASE WHEN quarter='Q4' THEN cv END) /
                        NULLIF(AVG(CASE WHEN quarter!='Q4' THEN cv END), 0), 1) AS q4_multiplier
                FROM contracts WHERE {scope_filter} AND instrument_type='C'
                GROUP BY department HAVING COUNT(*) >= 200
                ORDER BY q4_multiplier DESC LIMIT 5
            """)
            if not dept.empty:
                fig_dept.add_trace(go.Bar(x=dept["dept_name"], y=dept["q4_multiplier"],
                    marker_color=[RED if v > 2 else ORANGE if v > 1.5 else BLUE for v in dept["q4_multiplier"]],
                    text=[f"{v}x" for v in dept["q4_multiplier"]], textposition="outside", cliponaxis=False,
                    showlegend=False), row=1, col=i+1)
        fig_dept.add_hline(y=1.0, line_dash="dash", line_color=GRAY)
        fig_dept.update_layout(height=500, template="plotly_white",
            title="Top departments by Q4 value multiplier", margin=dict(t=60, b=120))
        fig_dept.update_yaxes(title_text="Q4 avg / Q1-Q3 avg", row=1, col=1)
        fig_dept.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_dept, use_container_width=True)
        st.caption("Departments where Q4 contract values are highest relative to other quarters. 1.0x = no difference.")

    # Finding + actions
    col_f, col_w, col_a = st.columns(3)
    with col_f:
        st.markdown('<div class="finding-box">'
            "<b>The pattern</b><br>"
            "- Q4 sees 20% more procurement activity post-2019<br>"
            "- Construction contracts average 5.84x higher in Q4 (post-2019)<br>"
            "- Amendments more concentrated in Q4 (32.7%) than new contracts (27.5%)<br>"
            "- Sole-source rate higher in Q4 (41.3% vs 39.1%)"
            '</div>', unsafe_allow_html=True)
    with col_w:
        st.markdown('<div class="insight-box">'
            "<b>Why it matters</b><br>"
            "- 'Use it or lose it' budget behaviour<br>"
            "- Departments rush to spend before March 31 or risk losing next year's budget<br>"
            "- Leads to less competition, oversized awards, and poorly scoped contracts<br>"
            "- Sets up the amendment growth in Insight 2"
            '</div>', unsafe_allow_html=True)
    with col_a:
        st.markdown('<div class="action-box">'
            "<b>What to do</b><br>"
            "- Q3 early warning: alert departments whose Q1-Q3 spending is low relative to budget<br>"
            "- Flag high-value Q4 construction contracts for additional review<br>"
            "- Track Q4 sole-source rates by department<br>"
            "- Consider multi-year budgeting for recurring needs"
            '</div>', unsafe_allow_html=True)

# ===================================================================
# INSIGHT 2: Amendment Growth
# ===================================================================

with tab2:
    st.header("Contracts grow far beyond original scope")

    # Headline metrics
    amend_row = fetch_one(f"""
        SELECT ROUND(SUM(CASE WHEN instrument_type='A' AND era IN ('2019-2022','Post-2022') THEN 1 ELSE 0 END)*100.0 /
                NULLIF(SUM(CASE WHEN era IN ('2019-2022','Post-2022') THEN 1 ELSE 0 END), 0), 1)
        FROM contracts WHERE {cf}
    """)
    amendment_dollars = fetch_one(f"""
        WITH g AS (
            SELECT TRY_CAST(MIN(original_value) AS DOUBLE) AS orig,
                TRY_CAST(MAX(contract_value) AS DOUBLE) AS final_val
            FROM contracts WHERE {cf} AND era IN ('2019-2022','Post-2022') AND procurement_id IS NOT NULL
            GROUP BY procurement_id
            HAVING COUNT(*) > 1 AND COUNT(DISTINCT instrument_type) > 1
        )
        SELECT ROUND((SUM(final_val) - SUM(orig))/1e9, 1) FROM g WHERE orig > 0
    """)
    comp_vs_sole = fetch_one(f"""
        SELECT
            ROUND(SUM(CASE WHEN solicitation_procedure='TC' AND instrument_type='A' THEN 1 ELSE 0 END)*100.0 /
                NULLIF(SUM(CASE WHEN solicitation_procedure='TC' THEN 1 ELSE 0 END), 0), 1),
            ROUND(SUM(CASE WHEN solicitation_procedure='TN' AND instrument_type='A' THEN 1 ELSE 0 END)*100.0 /
                NULLIF(SUM(CASE WHEN solicitation_procedure='TN' THEN 1 ELSE 0 END), 0), 1)
        FROM contracts WHERE {cf} AND era IN ('2019-2022','Post-2022')
    """)
    am1, am2, am3 = st.columns(3)
    am1.metric("Amendment Rate (post-2019)", f"{amend_row[0]:.1f}%" if amend_row[0] else "N/A")
    am2.metric("$ Added Through Amendments", f"${amendment_dollars[0]:.1f}B" if amendment_dollars[0] else "N/A")
    am3.metric("Competitive vs Sole-Source", f"{comp_vs_sole[0]:.1f}% vs {comp_vs_sole[1]:.1f}%" if comp_vs_sole[0] else "N/A")

    st.markdown('<div class="insight-box">'
        "- Amendments modify existing contracts after award<br>"
        "- Rate jumped from 16% to 25% of all transactions since 2019<br>"
        "- Some contracts grow by thousands of percent"
        '</div>', unsafe_allow_html=True)

    # Row 1: Amendment rate over time (inherently shows all years as a time series)
    amend_rate = fetch_df(f"""
        SELECT fiscal_year,
            ROUND(SUM(CASE WHEN instrument_type='A' THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS amend_pct
        FROM contracts WHERE {cf} AND fiscal_year != '2018-2018'
            AND fiscal_year >= '2010-2011' AND fiscal_year <= '2024-2025'
        GROUP BY fiscal_year HAVING COUNT(*) > 500 ORDER BY fiscal_year
    """)

    if not amend_rate.empty:
        fig_ar = go.Figure()
        fig_ar.add_trace(go.Scatter(x=amend_rate["fiscal_year"], y=amend_rate["amend_pct"],
            mode="lines+markers+text", line=dict(color=ORANGE, width=3), marker=dict(size=7),
            text=[f"{v}%" for v in amend_rate["amend_pct"]], textposition="top center",
            textfont=dict(size=10),
            hovertemplate="<b>%{x}</b><br>Amendment rate: %{y:.1f}%<extra></extra>"))
        fig_ar.add_hline(y=20, line_dash="dash", line_color=GRAY, annotation_text="20% baseline")
        fig_ar.add_vrect(x0="2019-2020", x1="2024-2025", fillcolor=BLUE, opacity=0.05,
            annotation_text="Mandatory reporting", annotation_position="top left")
        fig_ar.update_layout(title=f"Amendment rate by fiscal year ({commodity_label})",
            yaxis_title="% of rows that are amendments", template="plotly_white",
            height=380, xaxis_tickangle=-45)
        st.plotly_chart(fig_ar, use_container_width=True)
        st.caption("Rate jumped from ~16% to ~25% after 2019 when reporting became mandatory. The shaded area marks the mandatory reporting era.")

    # Row 2: Growth distribution by scope
    fig_growth = make_subplots(rows=1, cols=3, subplot_titles=SCOPE_NAMES, shared_yaxes=True)
    for i, (scope_name, scope_filter) in enumerate(SCOPES):
        growth = fetch_df(f"""
            WITH g AS (
                SELECT ROUND((TRY_CAST(MAX(contract_value) AS DOUBLE) /
                    NULLIF(TRY_CAST(MIN(original_value) AS DOUBLE), 0) - 1) * 100, 0) AS pct
                FROM contracts WHERE {scope_filter} AND procurement_id IS NOT NULL
                GROUP BY procurement_id
                HAVING COUNT(*) > 1 AND COUNT(DISTINCT instrument_type) > 1
            )
            SELECT CASE
                WHEN pct <= 50 THEN '1-50%'
                WHEN pct <= 100 THEN '51-100%'
                WHEN pct <= 500 THEN '101-500%'
                ELSE '500%+'
            END AS bucket, COUNT(*) AS cnt,
            ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(), 1) AS share
            FROM g WHERE pct IS NOT NULL AND pct > 0
            GROUP BY bucket ORDER BY MIN(pct)
        """)
        if not growth.empty:
            color_map = {"1-50%": BLUE, "51-100%": BLUE, "101-500%": ORANGE, "500%+": RED}
            fig_growth.add_trace(go.Bar(
                y=growth["bucket"], x=growth["share"], orientation="h",
                marker_color=[color_map.get(b, GRAY) for b in growth["bucket"]],
                text=[f"{s}%" for s in growth["share"]],
                textposition="outside", cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Share: %{x:.1f}%<extra></extra>", showlegend=False), row=1, col=i+1)
    fig_growth.update_layout(title="How much do amended contracts grow?",
        template="plotly_white", height=420, margin=dict(t=60))
    fig_growth.update_yaxes(autorange="reversed")
    fig_growth.update_xaxes(title_text="% of amended contracts", row=1, col=2)
    st.plotly_chart(fig_growth, use_container_width=True)
    st.caption("Only contracts that grew in value. Orange/red = more than doubled - these effectively bypass the original competitive process.")

    # Row 3: Top departments by amendment rate by scope
    if selected_dept == "All Departments":
        fig_dept_amend = make_subplots(rows=1, cols=3, subplot_titles=SCOPE_NAMES, shared_yaxes=True)
        for i, (scope_name, scope_filter) in enumerate(SCOPES):
            dept_amend = fetch_df(f"""
                SELECT LEFT(department, 20) AS dept_name,
                    ROUND(SUM(CASE WHEN instrument_type='A' THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS amend_rate
                FROM contracts WHERE {scope_filter}
                GROUP BY department HAVING COUNT(*) >= 1000
                ORDER BY amend_rate DESC LIMIT 5
            """)
            if not dept_amend.empty:
                fig_dept_amend.add_trace(go.Bar(x=dept_amend["dept_name"], y=dept_amend["amend_rate"],
                    marker_color=[RED if v > 40 else ORANGE if v > 30 else BLUE for v in dept_amend["amend_rate"]],
                    text=[f"{v}%" for v in dept_amend["amend_rate"]], textposition="outside", cliponaxis=False,
                    showlegend=False), row=1, col=i+1)
        fig_dept_amend.update_layout(height=500, template="plotly_white",
            title="Top departments by amendment rate", margin=dict(t=60, b=120))
        fig_dept_amend.update_yaxes(title_text="Amendment rate (%)", row=1, col=1)
        fig_dept_amend.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_dept_amend, use_container_width=True)
        st.caption("Departments with the highest share of amendment rows. CRA has more amendments than new contracts post-2019.")

    # Row 4: Top grown contracts (all years)
    st.subheader("Largest contract growth (excl. Defence)")
    top_grown = fetch_df(f"""
        SELECT procurement_id, MAX(vendor_name) AS vendor,
            MAX(department) AS department,
            COUNT(*) - 1 AS amendments,
            ROUND(TRY_CAST(MIN(original_value) AS DOUBLE)/1e6, 1) AS original_M,
            ROUND(TRY_CAST(MAX(contract_value) AS DOUBLE)/1e6, 1) AS final_M,
            ROUND((TRY_CAST(MAX(contract_value) AS DOUBLE) / NULLIF(TRY_CAST(MIN(original_value) AS DOUBLE), 0) - 1) * 100, 0) AS growth_pct
        FROM contracts WHERE {cf} AND procurement_id IS NOT NULL
        GROUP BY procurement_id HAVING COUNT(*) > 1
        ORDER BY TRY_CAST(MAX(contract_value) AS DOUBLE) - TRY_CAST(MIN(original_value) AS DOUBLE) DESC
        LIMIT 5
    """)

    if not top_grown.empty:
        display = top_grown.rename(columns={
            "procurement_id": "Contract ID", "vendor": "Vendor", "department": "Department",
            "amendments": "Amendments", "original_M": "Original ($M)", "final_M": "Final ($M)", "growth_pct": "Growth %"
        })
        st.dataframe(display, use_container_width=True, hide_index=True,
            column_config={
                "Original ($M)": st.column_config.NumberColumn(format="$%.1fM"),
                "Final ($M)": st.column_config.NumberColumn(format="$%.1fM"),
                "Growth %": st.column_config.NumberColumn(format="%,.0f%%"),
            })

    # Finding + actions
    col_f2, col_w2, col_a2 = st.columns(3)
    with col_f2:
        st.markdown('<div class="finding-box">'
            "<b>The pattern</b><br>"
            "- ~25% of all rows are amendments post-2019<br>"
            "- $13.4B added through amendments post-2019 (46% growth)<br>"
            "- Competitive contracts amended more (26.2%) than sole-source (14.3%)<br>"
            "- CRA (51%), IRCC (46.7%), ESDC (44.8%) lead in amendment rates"
            '</div>', unsafe_allow_html=True)
    with col_w2:
        st.markdown('<div class="insight-box">'
            "<b>Why it matters</b><br>"
            "- $13.4B in growth without re-competing<br>"
            "- Competitive contracts get amended more - consistent with low-bid-then-expand<br>"
            "- Q4-rushed contracts are more likely to need scope changes later<br>"
            "- Creates a pipeline from budget pressure to uncompeted growth"
            '</div>', unsafe_allow_html=True)
    with col_a2:
        st.markdown('<div class="action-box">'
            "<b>What to do</b><br>"
            "- Set amendment thresholds (e.g., re-compete at 50% growth)<br>"
            "- Separate routine from material amendments by size<br>"
            "- Focus oversight on services (highest growth risk)<br>"
            "- Monitor Q4 amendments as a compounding risk"
            '</div>', unsafe_allow_html=True)

# ===================================================================
# INSIGHT 3: Vendor Concentration
# ===================================================================

with tab3:
    st.header("Spending is concentrated in a few vendors - and they get amended more")

    # Headline metrics
    vc_row = fetch_one(f"""
        WITH v AS (
            SELECT vendor_name, SUM(cv) as total_val,
                   ROW_NUMBER() OVER (ORDER BY SUM(cv) DESC) as rn
            FROM contracts WHERE {cf} AND vendor_name IS NOT NULL
            GROUP BY vendor_name
        ),
        gt AS (SELECT SUM(total_val) as g FROM v)
        SELECT ROUND(SUM(CASE WHEN rn<=50 THEN total_val ELSE 0 END)*100.0/(SELECT g FROM gt), 1),
            COUNT(*)
        FROM v
    """)
    conc_trend = fetch_one(f"""
        WITH v AS (
            SELECT vendor_name, SUM(cv) as total_val,
                   ROW_NUMBER() OVER (ORDER BY SUM(cv) DESC) as rn
            FROM contracts WHERE {cf} AND vendor_name IS NOT NULL
            GROUP BY vendor_name
        )
        SELECT
            ROUND(SUM(CASE WHEN c.fiscal_year='2019-2020' AND v.rn<=50 THEN cv ELSE 0 END)*100.0 /
                NULLIF(SUM(CASE WHEN c.fiscal_year='2019-2020' THEN cv ELSE 0 END), 0), 1),
            ROUND(SUM(CASE WHEN c.fiscal_year='2024-2025' AND v.rn<=50 THEN cv ELSE 0 END)*100.0 /
                NULLIF(SUM(CASE WHEN c.fiscal_year='2024-2025' THEN cv ELSE 0 END), 0), 1)
        FROM contracts c
        JOIN v ON c.vendor_name = v.vendor_name
        WHERE {cf}
    """)
    per_contract = fetch_one(f"""
        WITH v AS (
            SELECT vendor_name, SUM(cv) as total_val,
                   ROW_NUMBER() OVER (ORDER BY SUM(cv) DESC) as rn
            FROM contracts WHERE {cf} AND vendor_name IS NOT NULL
            GROUP BY vendor_name
        ),
        growth AS (
            SELECT CASE WHEN v.rn <= 50 THEN 'Top 50' ELSE 'Others' END as tier,
                TRY_CAST(MIN(original_value) AS DOUBLE) AS orig,
                TRY_CAST(MAX(contract_value) AS DOUBLE) AS final_val
            FROM contracts c
            JOIN v ON c.vendor_name = v.vendor_name
            WHERE {cf} AND era IN ('2019-2022','Post-2022') AND procurement_id IS NOT NULL
            GROUP BY tier, procurement_id
            HAVING COUNT(*) > 1 AND COUNT(DISTINCT instrument_type) > 1
        )
        SELECT ROUND(AVG(CASE WHEN tier='Top 50' THEN final_val - orig END)/1e6, 1),
            ROUND(AVG(CASE WHEN tier='Others' THEN final_val - orig END)/1e3, 0)
        FROM growth WHERE orig > 0
    """)
    vm1, vm2, vm3 = st.columns(3)
    vm1.metric("Top 50 Share of Spend", f"{vc_row[0]:.1f}%" if vc_row[0] else "N/A")
    vm2.metric("Concentration Trend (2019 to 2024)",
        f"{conc_trend[0]:.0f}% to {conc_trend[1]:.0f}%" if conc_trend[0] and conc_trend[1] else "N/A")
    vm3.metric("Avg Amendment Growth: Top 50 vs Others",
        f"${per_contract[0]:.1f}M vs ${per_contract[1]:.0f}K" if per_contract[0] else "N/A")

    st.markdown('<div class="insight-box">'
        "- 126,000+ vendors in the dataset - is spending spread broadly or concentrated?<br>"
        "- Do the biggest vendors benefit disproportionately from amendments (Insight 2)?"
        '</div>', unsafe_allow_html=True)

    # Row 1: Vendor concentration by scope
    fig_conc = make_subplots(rows=1, cols=3, subplot_titles=SCOPE_NAMES, shared_yaxes=True)
    for i, (scope_name, scope_filter) in enumerate(SCOPES):
        conc = fetch_df(f"""
            WITH v AS (
                SELECT vendor_name, SUM(cv) as total_val,
                       ROW_NUMBER() OVER (ORDER BY SUM(cv) DESC) as rn
                FROM contracts WHERE {scope_filter} AND vendor_name IS NOT NULL
                GROUP BY vendor_name
            ),
            gt AS (SELECT SUM(total_val) as g FROM v)
            SELECT
                'Top 10' AS tier, ROUND(SUM(total_val)*100.0/(SELECT g FROM gt), 1) AS pct FROM v WHERE rn<=10
            UNION ALL SELECT
                'Top 50', ROUND(SUM(total_val)*100.0/(SELECT g FROM gt), 1) FROM v WHERE rn<=50
            UNION ALL SELECT
                'Top 100', ROUND(SUM(total_val)*100.0/(SELECT g FROM gt), 1) FROM v WHERE rn<=100
            UNION ALL SELECT
                'Top 500', ROUND(SUM(total_val)*100.0/(SELECT g FROM gt), 1) FROM v WHERE rn<=500
        """)
        if not conc.empty:
            fig_conc.add_trace(go.Bar(
                x=conc["tier"], y=conc["pct"],
                marker_color=[RED, ORANGE, BLUE, BLUE],
                text=[f"{v}%" for v in conc["pct"]], textposition="outside", cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Share: %{y:.1f}%<extra></extra>", showlegend=False), row=1, col=i+1)
    fig_conc.update_layout(title="Vendor concentration",
        template="plotly_white", height=400, margin=dict(t=60))
    fig_conc.update_yaxes(title_text="% of total spend", row=1, col=1)
    st.plotly_chart(fig_conc, use_container_width=True)
    st.caption("A small number of vendors capture a disproportionate share of spending across all eras.")

    # Row 2: Amendment rate by vendor tier by scope
    fig_tier = make_subplots(rows=1, cols=3, subplot_titles=SCOPE_NAMES, shared_yaxes=True)
    for i, (scope_name, scope_filter) in enumerate(SCOPES):
        tier_amend = fetch_df(f"""
            WITH v AS (
                SELECT vendor_name, SUM(cv) as total_val,
                       ROW_NUMBER() OVER (ORDER BY SUM(cv) DESC) as rn
                FROM contracts WHERE {scope_filter} AND vendor_name IS NOT NULL
                GROUP BY vendor_name
            )
            SELECT
                CASE WHEN v.rn <= 50 THEN 'Top 50 vendors' ELSE 'All others' END as tier,
                COUNT(*) as rows,
                ROUND(100.0 * SUM(CASE WHEN c.instrument_type='A' THEN 1 ELSE 0 END) / COUNT(*), 1) as amend_rate
            FROM contracts c
            JOIN v ON c.vendor_name = v.vendor_name
            WHERE {scope_filter}
            GROUP BY CASE WHEN v.rn <= 50 THEN 'Top 50 vendors' ELSE 'All others' END
            ORDER BY MIN(v.rn)
        """)
        if not tier_amend.empty:
            fig_tier.add_trace(go.Bar(
                x=tier_amend["tier"], y=tier_amend["amend_rate"],
                marker_color=[RED, BLUE],
                text=[f"{v}%" for v in tier_amend["amend_rate"]], textposition="outside", cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Amendment rate: %{y:.1f}%<extra></extra>", showlegend=False), row=1, col=i+1)
    fig_tier.update_layout(title="Amendment rate by vendor tier",
        template="plotly_white", height=400, margin=dict(t=60))
    fig_tier.update_yaxes(title_text="Amendment rate (%)", row=1, col=1)
    st.plotly_chart(fig_tier, use_container_width=True)
    st.caption("Top vendors consistently have higher amendment rates, meaning they benefit from both the initial award and subsequent scope expansion.")

    # Row 3: Department dependency (all years)
    st.subheader("Single-vendor dependency by department")
    dept_dep = fetch_df(f"""
        WITH dept_vendor AS (
            SELECT department, vendor_name, SUM(cv) as vendor_total,
                   SUM(SUM(cv)) OVER (PARTITION BY department) as dept_total,
                   ROW_NUMBER() OVER (PARTITION BY department ORDER BY SUM(cv) DESC) as rn
            FROM contracts WHERE {cf} AND vendor_name IS NOT NULL AND cv > 0
            GROUP BY department, vendor_name
        )
        SELECT department,
               vendor_name AS top_vendor,
               ROUND(dept_total/1e9, 2) AS dept_total_B,
               ROUND(vendor_total/1e9, 2) AS vendor_total_B,
               ROUND(100.0 * vendor_total / dept_total, 1) AS dependency_pct
        FROM dept_vendor
        WHERE rn = 1 AND dept_total > 1e9
        ORDER BY dependency_pct DESC
        LIMIT 10
    """)

    if not dept_dep.empty:
        st.dataframe(dept_dep.rename(columns={
            "department": "Department", "top_vendor": "Top Vendor",
            "dept_total_B": "Dept Total ($B)", "vendor_total_B": "Vendor ($B)",
            "dependency_pct": "Dependency %"
        }), use_container_width=True, hide_index=True,
        column_config={
            "Dept Total ($B)": st.column_config.NumberColumn(format="$%.2fB"),
            "Vendor ($B)": st.column_config.NumberColumn(format="$%.2fB"),
            "Dependency %": st.column_config.NumberColumn(format="%.1f%%"),
        })

    # Finding + actions
    col_f3, col_w3, col_a3 = st.columns(3)
    with col_f3:
        st.markdown('<div class="finding-box">'
            "<b>The pattern</b><br>"
            "- Top 50 share grew from 45% (2019) to 70% (2024) - concentration is accelerating<br>"
            "- Top 50 avg amendment adds $3M per contract vs $158K for others<br>"
            "- Top vendors don't rely on sole-source (32.9%) - they win competitively then expand<br>"
            "- Deloitte is top vendor for both ESDC (37%) and CBSA (37%)"
            '</div>', unsafe_allow_html=True)
    with col_w3:
        st.markdown('<div class="insight-box">'
            "<b>Why it matters</b><br>"
            "- Concentration is getting worse, not stabilizing<br>"
            "- Top vendors grow through amendments, not sole-source - harder to catch<br>"
            "- Same vendors dominating multiple departments creates systemic risk<br>"
            "- Completes the cycle: Q4 rush, amendment growth, vendor concentration"
            '</div>', unsafe_allow_html=True)
    with col_a3:
        st.markdown('<div class="action-box">'
            "<b>What to do</b><br>"
            "- Map vendor dependency for critical services<br>"
            "- Flag departments where one vendor holds >30% of spend<br>"
            "- Diversify vendor base for recurring contract categories<br>"
            "- Monitor whether top-vendor contracts are amended at higher rates"
            '</div>', unsafe_allow_html=True)

# ===================================================================
# Next Steps
# ===================================================================

with tab5:
    st.header("What I'd investigate next")

    ns1, ns2 = st.columns(2)

    with ns1:
        st.markdown('<div class="insight-box">'
            "<b>1. Test the causal chain: Q4 rush to amendments</b><br>"
            "- Are contracts <i>awarded</i> in Q4 amended more in later quarters?<br>"
            "- Would confirm that year-end rush causes poorly scoped contracts<br>"
            "- Direct causal link between Insight 1 and Insight 2"
            '</div>', unsafe_allow_html=True)

        st.markdown('<div class="insight-box">'
            "<b>2. Do top vendors bid low and grow through amendments?</b><br>"
            "- Compare original vs. final values by vendor tier<br>"
            "- If top vendors consistently win low and grow high, it suggests strategic low-bidding<br>"
            "- Would inform bid evaluation criteria"
            '</div>', unsafe_allow_html=True)

    with ns2:
        st.markdown('<div class="insight-box">'
            "<b>3. Department-level risk scores</b><br>"
            "- Combine Q4 surge, amendment rate, and vendor concentration into one score per department<br>"
            "- Identifies which departments have the worst combination of all three risks<br>"
            "- Prioritizes oversight where it matters most"
            '</div>', unsafe_allow_html=True)

        st.markdown('<div class="insight-box">'
            "<b>4. Local economic intelligence - the Halton share</b><br>"
            "- Filter <code>vendor_postal_code</code> (mandatory post-2019) by Halton prefixes (L6, L7, L9)<br>"
            "- Identify how much federal contract money flows into Oakville, Burlington, Milton, Halton Hills<br>"
            "- Reveal which local industries are winning federal business<br>"
            "- Give Economic Development concrete data to attract similar companies"
            '</div>', unsafe_allow_html=True)

st.markdown("---")
st.caption("Data: Government of Canada Proactive Disclosure of Contracts Over $10,000")
