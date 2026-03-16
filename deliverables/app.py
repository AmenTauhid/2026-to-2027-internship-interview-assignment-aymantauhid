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
LIGHT_GRAY = "#CCCCCC"
BG = "#FAFBFC"

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

    selected_era = st.selectbox("Reporting Era", ["All Years", "Post-2019", "Pre-2019"],
        help="Post-2019: mandatory reporting, most reliable. Pre-2019: voluntary, commodity_type and instrument_type not mandatory.")
    selected_commodity = st.selectbox("Commodity Type", ["All", "Services", "Goods", "Construction"],
        help="commodity_type not mandatory before 2019. Pre-2019 breakdown is incomplete.")

    st.markdown("---")
    st.markdown("**Scope**")
    st.markdown(
        "- National Defence excluded\n"
        "- Valid reporting periods only\n"
        "- `commodity_type`, `instrument_type` mandatory post-2019 only\n"
        "- All values in CAD (nominal)"
    )

    st.markdown("---")
    st.caption("Built with DuckDB, Plotly, Streamlit")
    st.caption("Analysis by Ayman Tauhid")

COMMODITY_MAP = {"Services": "S", "Goods": "G", "Construction": "C"}

def combined_filter():
    parts = []
    if selected_era == "Post-2019":
        parts.append("era IN ('2019-2022', 'Post-2022')")
    elif selected_era == "Pre-2019":
        parts.append("era = 'Pre-2019'")
    if selected_commodity != "All":
        parts.append(f"commodity_type = '{COMMODITY_MAP[selected_commodity]}'")
    return " AND ".join(parts) if parts else "1=1"

f = combined_filter()

ERA_LABELS = {"Post-2019": "2019-2025", "Pre-2019": "2004-2019", "All Years": "2004-2025"}
era_label = ERA_LABELS.get(selected_era, "2004-2025")
commodity_label = selected_commodity if selected_commodity != "All" else "All commodities"

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("What can we learn from federal contract data?")
st.markdown("Three insights from 1.26 million rows of Government of Canada procurement data (excl. National Defence, valid reporting periods).")

# ---------------------------------------------------------------------------
# Overview metrics
# ---------------------------------------------------------------------------

row_total = fetch_one(f"SELECT COUNT(*) FROM contracts WHERE {f}")[0]
unique_contracts = fetch_one(f"SELECT COUNT(DISTINCT procurement_id) FROM contracts WHERE {f} AND procurement_id IS NOT NULL")[0]
total_value = fetch_one(f"SELECT SUM(cv) FROM contracts WHERE {f}")[0] or 0
unique_vendors = fetch_one(f"SELECT COUNT(DISTINCT vendor_name) FROM contracts WHERE {f}")[0]
contracts_only = fetch_one(f"SELECT COUNT(*) FROM contracts WHERE {f} AND instrument_type='C'")[0]
amendments_only = fetch_one(f"SELECT COUNT(*) FROM contracts WHERE {f} AND instrument_type='A'")[0]

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Rows", f"{row_total:,.0f}")
c2.metric("Contracts", f"{contracts_only:,.0f}")
c3.metric("Amendments", f"{amendments_only:,.0f}")
c4.metric("Total Value", f"${total_value/1e9:,.1f}B")
c5.metric("Vendors", f"{unique_vendors:,.0f}")
c6.metric("Amendment Rate", f"{amendments_only*100/row_total:.1f}%")

st.markdown("---")

# ===================================================================
# INSIGHT 1: Q4 Spending Surge
# ===================================================================

st.header("Insight 1: Fiscal year-end spending surge")

st.markdown('<div class="insight-box">'
    "Canada's fiscal year ends March 31. Q4 (January-March) is the final quarter "
    "before budgets reset. If departments rush to spend, it should show up as more "
    "contracts and higher values in Q4."
    '</div>', unsafe_allow_html=True)

# Row 1: Q4 overview - count + avg value side by side
qtr = fetch_df(f"""
    SELECT quarter, COUNT(*) AS cnt, ROUND(AVG(cv), 0) AS avg_val,
        ROUND(SUM(cv)/1e9, 2) AS total_B
    FROM contracts WHERE {f} AND instrument_type='C'
    GROUP BY quarter ORDER BY quarter
""")

if not qtr.empty:
    labels = {"Q1": "Q1 (Apr-Jun)", "Q2": "Q2 (Jul-Sep)", "Q3": "Q3 (Oct-Dec)", "Q4": "Q4 (Jan-Mar)"}
    qtr["label"] = qtr["quarter"].map(labels)
    colors = [BLUE if q != "Q4" else RED for q in qtr["quarter"]]

    fig = make_subplots(rows=1, cols=2, subplot_titles=(f"Contract Count by Quarter ({era_label})", f"Average Contract Value by Quarter ({era_label})"))

    fig.add_trace(go.Bar(x=qtr["label"], y=qtr["cnt"], marker_color=colors,
        text=[f"{v:,.0f}" for v in qtr["cnt"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>Count: %{y:,.0f}<extra></extra>", showlegend=False), row=1, col=1)

    fig.add_trace(go.Bar(x=qtr["label"], y=qtr["avg_val"], marker_color=colors,
        text=[f"${v/1000:.0f}K" for v in qtr["avg_val"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>Avg: $%{y:,.0f}<extra></extra>", showlegend=False), row=1, col=2)

    fig.update_layout(height=430, template="plotly_white", margin=dict(t=50, b=10))
    fig.update_yaxes(rangemode="tozero", automargin=True)
    st.plotly_chart(fig, use_container_width=True)

# Row 2: Commodity breakdown + instrument type breakdown
col_left, col_right = st.columns(2)

with col_left:
    comm_q4 = fetch_df(f"""
        SELECT CASE commodity_type WHEN 'S' THEN 'Services' WHEN 'G' THEN 'Goods' WHEN 'C' THEN 'Construction' END AS commodity,
            ROUND(AVG(CASE WHEN quarter='Q4' THEN cv END), 0) AS q4_avg,
            ROUND(AVG(CASE WHEN quarter!='Q4' THEN cv END), 0) AS other_avg
        FROM contracts WHERE {f} AND instrument_type='C' AND commodity_type IN ('S','G','C')
        GROUP BY commodity_type ORDER BY commodity_type
    """)

    if not comm_q4.empty:
        fig_c = go.Figure()
        fig_c.add_trace(go.Bar(name="Q1-Q3", x=comm_q4["commodity"], y=comm_q4["other_avg"],
            marker_color=BLUE, text=[f"${v/1000:.0f}K" for v in comm_q4["other_avg"]], textposition="outside", cliponaxis=False))
        fig_c.add_trace(go.Bar(name="Q4", x=comm_q4["commodity"], y=comm_q4["q4_avg"],
            marker_color=RED, text=[f"${v/1000:.0f}K" for v in comm_q4["q4_avg"]], textposition="outside", cliponaxis=False))
        max_val = max(comm_q4["q4_avg"].max(), comm_q4["other_avg"].max())
        fig_c.update_layout(barmode="group", title=f"Q4 avg value by commodity - new contracts only ({era_label})", height=420,
            template="plotly_white", yaxis_title="Avg contract value ($)",
            yaxis=dict(range=[0, max_val * 1.25]))
        st.plotly_chart(fig_c, use_container_width=True)

with col_right:
    inst_q4 = fetch_df(f"""
        SELECT CASE instrument_type WHEN 'C' THEN 'New Contracts' WHEN 'A' THEN 'Amendments' WHEN 'SOSA' THEN 'Standing Offers' END AS type,
            ROUND(SUM(CASE WHEN quarter='Q4' THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS q4_pct
        FROM contracts WHERE {f} AND instrument_type IN ('A','C','SOSA')
        GROUP BY instrument_type ORDER BY q4_pct DESC
    """)

    if not inst_q4.empty:
        fig_i = go.Figure(go.Bar(x=inst_q4["type"], y=inst_q4["q4_pct"],
            marker_color=[RED if p > 30 else ORANGE if p > 25 else BLUE for p in inst_q4["q4_pct"]],
            text=[f"{v}%" for v in inst_q4["q4_pct"]], textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Q4 share: %{y:.1f}%<extra></extra>"))
        fig_i.add_hline(y=25, line_dash="dash", line_color=GRAY, annotation_text="Expected 25%")
        fig_i.update_layout(title=f"Q4 share by transaction type ({era_label})", height=380,
            template="plotly_white", yaxis_title="% in Q4")
        st.plotly_chart(fig_i, use_container_width=True)

# Row 3: Year-over-year trend
yoy = fetch_df(f"""
    SELECT fiscal_year,
        ROUND(AVG(CASE WHEN quarter='Q4' THEN cv END), 0) AS q4_avg,
        ROUND(AVG(CASE WHEN quarter!='Q4' THEN cv END), 0) AS other_avg
    FROM contracts WHERE {f} AND instrument_type='C' AND cv > 0
        AND fiscal_year != '2018-2018' AND fiscal_year >= '2017-2018' AND fiscal_year <= '2024-2025'
    GROUP BY fiscal_year HAVING COUNT(*) > 100 ORDER BY fiscal_year
""")

if not yoy.empty:
    fig_yoy = go.Figure()
    fig_yoy.add_trace(go.Scatter(x=yoy["fiscal_year"], y=yoy["other_avg"], mode="lines+markers",
        name="Q1-Q3 avg", line=dict(color=BLUE, width=2), marker=dict(size=7)))
    fig_yoy.add_trace(go.Scatter(x=yoy["fiscal_year"], y=yoy["q4_avg"], mode="lines+markers",
        name="Q4 avg", line=dict(color=RED, width=3), marker=dict(size=8)))
    fig_yoy.update_layout(title=f"Q4 vs Q1-Q3 average contract value over time ({commodity_label})",
        yaxis_title="Average contract value ($)", xaxis_title="Fiscal year",
        template="plotly_white", height=400, hovermode="x unified", xaxis_tickangle=-45)
    st.plotly_chart(fig_yoy, use_container_width=True)

# Finding + actions
col_f, col_w, col_a = st.columns(3)
with col_f:
    st.markdown('<div class="finding-box">'
        "<b>The pattern</b><br>"
        "Q4 sees 20% more procurement activity post-2019. "
        "Construction contracts average 5.84x higher in Q4 (post-2019), "
        "up from 3.4x across all years. "
        "Amendments are more concentrated in Q4 (32.7%) than new contracts (27.5%)."
        '</div>', unsafe_allow_html=True)
with col_w:
    st.markdown('<div class="insight-box">'
        "<b>Why it matters</b><br>"
        "Classic 'use it or lose it' budget behaviour. Departments rush to spend remaining budget before "
        "March 31 or risk losing it next fiscal year. This pressure leads to less competition "
        "(sole-source 41.3% vs 39.1%), oversized construction awards, and poorly scoped contracts "
        "that set up the amendment growth in Insight 2."
        '</div>', unsafe_allow_html=True)
with col_a:
    st.markdown('<div class="action-box">'
        "<b>What to do</b><br>"
        "- Flag high-value Q4 construction contracts for additional review<br>"
        "- Track Q4 sole-source rates by department<br>"
        "- Consider multi-year budgeting for recurring needs"
        '</div>', unsafe_allow_html=True)

st.markdown("---")

# ===================================================================
# INSIGHT 2: Amendment Growth
# ===================================================================

st.header("Insight 2: Contracts grow far beyond original scope")

st.markdown('<div class="insight-box">'
    "Amendments modify existing contracts after award. The rate has jumped from 16% to 25% "
    "of all transactions since 2019. Some contracts grow by thousands of percent."
    '</div>', unsafe_allow_html=True)

# Row 1: Amendment rate over time
amend_rate = fetch_df(f"""
    SELECT fiscal_year,
        ROUND(SUM(CASE WHEN instrument_type='A' THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS amend_pct
    FROM contracts WHERE {f} AND fiscal_year != '2018-2018'
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
    fig_ar.update_layout(title=f"Amendment rate by fiscal year ({commodity_label})",
        yaxis_title="% of rows that are amendments", template="plotly_white",
        height=380, xaxis_tickangle=-45)
    st.plotly_chart(fig_ar, use_container_width=True)

# Row 2: Growth distribution + commodity type
col_left2, col_right2 = st.columns(2)

with col_left2:
    growth = fetch_df(f"""
        WITH g AS (
            SELECT ROUND((TRY_CAST(MAX(contract_value) AS DOUBLE) /
                NULLIF(TRY_CAST(MIN(original_value) AS DOUBLE), 0) - 1) * 100, 0) AS pct
            FROM contracts WHERE {f} AND procurement_id IS NOT NULL
            GROUP BY procurement_id
            HAVING COUNT(*) > 1 AND COUNT(DISTINCT instrument_type) > 1
        )
        SELECT CASE
            WHEN pct < 0 THEN 'Decreased'
            WHEN pct = 0 THEN 'No change'
            WHEN pct <= 50 THEN '1-50%'
            WHEN pct <= 100 THEN '51-100%'
            WHEN pct <= 500 THEN '101-500%'
            ELSE '500%+'
        END AS bucket, COUNT(*) AS cnt,
        ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(), 1) AS share
        FROM g WHERE pct IS NOT NULL
        GROUP BY bucket ORDER BY MIN(pct)
    """)

    if not growth.empty:
        color_map = {"Decreased": GREEN, "No change": GRAY, "1-50%": BLUE,
                     "51-100%": BLUE, "101-500%": ORANGE, "500%+": RED}
        fig_g = go.Figure(go.Bar(
            y=growth["bucket"], x=growth["share"], orientation="h",
            marker_color=[color_map.get(b, GRAY) for b in growth["bucket"]],
            text=[f"{s}% ({c:,})" for s, c in zip(growth["share"], growth["cnt"])],
            textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Share: %{x:.1f}%<extra></extra>"))
        fig_g.update_layout(title=f"How much do amended contracts grow? ({era_label})",
            xaxis_title="% of amended contracts", template="plotly_white",
            height=380, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_g, use_container_width=True)

with col_right2:
    amend_comm = fetch_df(f"""
        SELECT CASE commodity_type WHEN 'S' THEN 'Services' WHEN 'G' THEN 'Goods' WHEN 'C' THEN 'Construction' END AS commodity,
            ROUND(SUM(CASE WHEN instrument_type='A' THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS amend_pct
        FROM contracts WHERE {f} AND commodity_type IN ('S','G','C')
            AND fiscal_year >= '2019-2020'
        GROUP BY commodity_type ORDER BY amend_pct DESC
    """)

    if not amend_comm.empty:
        fig_ac = go.Figure(go.Bar(
            x=amend_comm["commodity"], y=amend_comm["amend_pct"],
            marker_color=[RED if p > 25 else ORANGE if p > 15 else BLUE for p in amend_comm["amend_pct"]],
            text=[f"{v}%" for v in amend_comm["amend_pct"]], textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Rate: %{y:.1f}%<extra></extra>"))
        fig_ac.update_layout(title=f"Amendment rate by commodity - post-2019 ({commodity_label})",
            yaxis_title="Amendment rate (%)", template="plotly_white", height=380)
        st.plotly_chart(fig_ac, use_container_width=True)

# Row 3: Top grown contracts
st.subheader("Largest contract growth (excl. Defence)")
top_grown = fetch_df(f"""
    SELECT procurement_id, MAX(vendor_name) AS vendor,
        SPLIT_PART(MAX(owner_org_title), ' | ', 1) AS department,
        COUNT(*) - 1 AS amendments,
        ROUND(TRY_CAST(MIN(original_value) AS DOUBLE)/1e6, 1) AS original_M,
        ROUND(TRY_CAST(MAX(contract_value) AS DOUBLE)/1e6, 1) AS final_M,
        ROUND((TRY_CAST(MAX(contract_value) AS DOUBLE) / NULLIF(TRY_CAST(MIN(original_value) AS DOUBLE), 0) - 1) * 100, 0) AS growth_pct
    FROM contracts WHERE {f} AND procurement_id IS NOT NULL
    GROUP BY procurement_id HAVING COUNT(*) > 1
    ORDER BY TRY_CAST(MAX(contract_value) AS DOUBLE) - TRY_CAST(MIN(original_value) AS DOUBLE) DESC
    LIMIT 8
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
        "~25% of all rows are amendments post-2019. "
        "Services: 31.4% amendment rate, median 38% growth. "
        "Amendments spike in Q4 (28.2% vs 23.3%) - year-end pressure drives scope expansion too."
        '</div>', unsafe_allow_html=True)
with col_w2:
    st.markdown('<div class="insight-box">'
        "<b>Why it matters</b><br>"
        "A contract that grows from $18.6M to $1B through 16 amendments has effectively bypassed "
        "the competitive process used for the original award. The Q4 connection makes it worse: "
        "contracts rushed at year-end are more likely to need scope changes later, "
        "creating a pipeline from budget pressure to uncompeted growth."
        '</div>', unsafe_allow_html=True)
with col_a2:
    st.markdown('<div class="action-box">'
        "<b>What to do</b><br>"
        "- Set amendment thresholds (e.g., re-compete at 50% growth)<br>"
        "- Separate routine from material amendments by size<br>"
        "- Focus oversight on services (highest growth risk)<br>"
        "- Monitor Q4 amendments as a compounding risk"
        '</div>', unsafe_allow_html=True)

st.markdown("---")

# ===================================================================
# INSIGHT 3: Vendor Concentration
# ===================================================================

st.header("Insight 3: Spending is concentrated in a few vendors - and they get amended more")

st.markdown('<div class="insight-box">'
    "With 126,000+ vendors in the dataset, is spending spread broadly or concentrated "
    "in a few? And do the biggest vendors benefit disproportionately from the amendment "
    "pattern we found in Insight 2?"
    '</div>', unsafe_allow_html=True)

# Row 1: Concentration curve + amendment rate by tier
col_v1, col_v2 = st.columns(2)

with col_v1:
    conc = fetch_df(f"""
        WITH v AS (
            SELECT vendor_name, SUM(cv) as total_val,
                   ROW_NUMBER() OVER (ORDER BY SUM(cv) DESC) as rn
            FROM contracts WHERE {f} AND vendor_name IS NOT NULL
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
        fig_conc = go.Figure(go.Bar(
            x=conc["tier"], y=conc["pct"],
            marker_color=[RED, ORANGE, BLUE, BLUE],
            text=[f"{v}%" for v in conc["pct"]], textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Share: %{y:.1f}%<extra></extra>"))
        fig_conc.update_layout(title=f"Vendor concentration ({era_label})",
            yaxis_title="% of total spend", template="plotly_white", height=380)
        st.plotly_chart(fig_conc, use_container_width=True)

with col_v2:
    tier_amend = fetch_df(f"""
        WITH v AS (
            SELECT vendor_name, SUM(cv) as total_val,
                   ROW_NUMBER() OVER (ORDER BY SUM(cv) DESC) as rn
            FROM contracts WHERE {f} AND vendor_name IS NOT NULL
            GROUP BY vendor_name
        )
        SELECT
            CASE WHEN v.rn <= 50 THEN 'Top 50 vendors' ELSE 'All others' END as tier,
            COUNT(*) as rows,
            ROUND(100.0 * SUM(CASE WHEN c.instrument_type='A' THEN 1 ELSE 0 END) / COUNT(*), 1) as amend_rate
        FROM contracts c
        JOIN v ON c.vendor_name = v.vendor_name
        WHERE {f}
        GROUP BY CASE WHEN v.rn <= 50 THEN 'Top 50 vendors' ELSE 'All others' END
        ORDER BY MIN(v.rn)
    """)

    if not tier_amend.empty:
        fig_ta = go.Figure(go.Bar(
            x=tier_amend["tier"], y=tier_amend["amend_rate"],
            marker_color=[RED, BLUE],
            text=[f"{v}%" for v in tier_amend["amend_rate"]], textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Amendment rate: %{y:.1f}%<extra></extra>"))
        fig_ta.update_layout(title=f"Amendment rate by vendor tier ({era_label})",
            yaxis_title="Amendment rate (%)", template="plotly_white", height=380)
        st.plotly_chart(fig_ta, use_container_width=True)

# Row 2: Department dependency
st.subheader("Single-vendor dependency by department")
dept_dep = fetch_df(f"""
    WITH dept_vendor AS (
        SELECT owner_org_title, vendor_name, SUM(cv) as vendor_total,
               SUM(SUM(cv)) OVER (PARTITION BY owner_org_title) as dept_total,
               ROW_NUMBER() OVER (PARTITION BY owner_org_title ORDER BY SUM(cv) DESC) as rn
        FROM contracts WHERE {f} AND vendor_name IS NOT NULL AND cv > 0
        GROUP BY owner_org_title, vendor_name
    )
    SELECT SPLIT_PART(owner_org_title, ' | ', 1) AS department,
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
        "Top 50 vendors (out of 126,000+) hold 55% of all spend. "
        "Their amendment rate is 38% - nearly double the 21% for others. "
        "18 departments have >30% of spend with a single vendor."
        '</div>', unsafe_allow_html=True)
with col_w3:
    st.markdown('<div class="insight-box">'
        "<b>Why it matters</b><br>"
        "Vendor lock-in reduces negotiating leverage and creates supply chain risk. "
        "The biggest vendors also get amended the most, meaning they benefit from both "
        "the initial award and the subsequent scope expansion. "
        "This completes the cycle: Q4 rush, amendment growth, vendor concentration."
        '</div>', unsafe_allow_html=True)
with col_a3:
    st.markdown('<div class="action-box">'
        "<b>What to do</b><br>"
        "- Map vendor dependency for critical services<br>"
        "- Flag departments where one vendor holds >30% of spend<br>"
        "- Diversify vendor base for recurring contract categories<br>"
        "- Monitor whether top-vendor contracts are amended at higher rates"
        '</div>', unsafe_allow_html=True)

st.markdown("---")

# ===================================================================
# How the insights connect
# ===================================================================

st.header("How the insights connect")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="insight-box">'
        "<b>Q4 pressure</b><br>"
        "Budget cycles create year-end rush. Construction values 3.4x higher in Q4 across all years, rising to 5.84x post-2019."
        '</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="insight-box">'
        "<b>Amendment expansion</b><br>"
        "Contracts grow beyond original scope. Top vendors have 38% amendment rate vs 21% for others."
        '</div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="insight-box">'
        "<b>Vendor concentration</b><br>"
        "Top 50 vendors hold 55% of spend and benefit the most from amendment growth - a self-reinforcing cycle."
        '</div>', unsafe_allow_html=True)

st.markdown("---")

# ===================================================================
# Data Quality
# ===================================================================

with st.expander("Data Quality, Limitations & Assumptions", expanded=False):
    dq1, dq2 = st.columns(2)
    with dq1:
        st.markdown("**Data completeness**")
        st.markdown(
            "| Scope | Reporting | Key limitation |\n|---|---|---|\n"
            "| Pre-2019 | Voluntary | `reporting_period`, `commodity_type`, `instrument_type` not mandatory. Volume counts inflated. |\n"
            "| Post-2019 | Mandatory | Core fields reliable. Primary evidence base. |\n"
            "| All Years | Combined | Shows long-term trends. Volume influenced by pre-2019 bias. |"
        )
        st.markdown("**Assumptions**")
        st.markdown(
            "- National Defence excluded (structurally different procurement)\n"
            "- `contract_value` on amendments = cumulative total, not incremental\n"
            "- Vendor names used as-is (no normalization) - concentration is conservatively estimated\n"
            "- `commodity_type` and `instrument_type` not mandatory before 2019 - commodity/transaction type breakdowns use post-2019 data\n"
            "- All values nominal CAD, not inflation-adjusted"
        )
    with dq2:
        st.markdown("**Data issues encountered**")
        malformed = fetch_one("SELECT COUNT(*) FROM raw WHERE reporting_period IS NOT NULL AND reporting_period NOT LIKE '____-____-Q_' AND owner_org_title NOT LIKE 'National Defence%'")[0]
        st.markdown(
            f"- **{malformed:,}** malformed `reporting_period` values excluded\n"
            "- **Vendor name inconsistency**: same vendor under multiple spellings (10+ variants for some). True vendor concentration is higher than reported.\n"
            "- **`reporting_period` = reporting date, not award date**: Q4 patterns could partly reflect reporting lag, but the pattern is too large and consistent to be explained by lag alone.\n"
            "- **28% of rows have no `instrument_type`**: older records before the field was mandatory. Excluded from contract/amendment analysis.\n"
            "- **Zero cast failures** on financial fields across all 1.26M rows."
        )

with st.expander("What I'd investigate next", expanded=False):
    st.markdown(
        "1. **Do Q4 contracts get amended more than Q1-Q3 contracts?** We showed amendments "
        "are more common *in* Q4, but are contracts *awarded* in Q4 more likely to be amended later?\n\n"
        "2. **Which contract descriptions drive the Q4 volume surge?** Temporary help, "
        "consulting, or other categories disproportionately rushed at year-end?\n\n"
        "3. **How do amendment patterns differ by contract size?** Is growth concentrated in "
        "high-value contracts?\n\n"
        "4. **Vendor-level amendment patterns** - do certain vendors receive disproportionately "
        "more amendments? Could indicate strategic low-bidding followed by scope expansion."
    )

st.caption("Data: Government of Canada Proactive Disclosure of Contracts Over $10,000")
