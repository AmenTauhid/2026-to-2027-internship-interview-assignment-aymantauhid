"""
Government of Canada Contracts - Analysis Dashboard
Streamlit dashboard for Halton Region internship interview presentation.
Author: Ayman Tauhid
"""

import os
import streamlit as st
import duckdb
import plotly.graph_objects as go
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv(override=True)
CSV_PATH = os.getenv("LOCAL_DATASET_PATH", "data/contracts.csv")

# Colour palette
BLUE = "#4878A8"
RED = "#D04040"
ORANGE = "#E8A040"
GREEN = "#6BAF6B"
GRAY = "#888888"
GRAY_LIGHT = "#CCCCCC"

st.set_page_config(
    page_title="Gov of Canada Contracts Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading dataset ...")
def load_data(csv_path: str) -> duckdb.DuckDBPyConnection:
    """Load the CSV into an in-memory DuckDB table and return a connection."""
    con = duckdb.connect()
    con.execute(f"""
        CREATE TABLE raw AS
        SELECT *
        FROM read_csv_auto(
            '{csv_path}',
            all_varchar = true,
            strict_mode = false,
            parallel = false
        )
    """)
    # Create the main working view: exclude National Defence, valid reporting_period only
    con.execute("""
        CREATE VIEW contracts AS
        SELECT *,
            -- parse fiscal year label from reporting_period (e.g. '2022-2023-Q1' -> '2022-2023')
            LEFT(reporting_period, 9) AS fiscal_year,
            -- parse quarter
            RIGHT(reporting_period, 2) AS quarter,
            -- numeric casts
            TRY_CAST(contract_value AS DOUBLE) AS cv,
            TRY_CAST(original_value AS DOUBLE) AS ov,
            TRY_CAST(amendment_value AS DOUBLE) AS av,
            -- era bucket
            CASE
                WHEN LEFT(reporting_period, 4)::INT < 2019 THEN 'Pre-2019'
                WHEN LEFT(reporting_period, 4)::INT < 2022 THEN '2019-2022'
                ELSE 'Post-2022'
            END AS era
        FROM raw
        WHERE reporting_period LIKE '____-____-Q_'
          AND owner_org_title NOT LIKE 'National Defence%'
    """)
    return con


def get_con() -> duckdb.DuckDBPyConnection:
    """Return a usable cursor from the cached connection."""
    return load_data(CSV_PATH)


# ---------------------------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------------------------

st.sidebar.title("Filters")

era_options = ["All", "Pre-2019", "2019-2022", "Post-2022"]
selected_era = st.sidebar.selectbox("Reporting era", era_options, index=0)

commodity_options = ["All", "Services", "Goods", "Construction"]
selected_commodity = st.sidebar.selectbox("Commodity type", commodity_options, index=0)

COMMODITY_MAP = {"Services": "S", "Goods": "G", "Construction": "C"}


def era_filter() -> str:
    if selected_era == "All":
        return "1=1"
    return f"era = '{selected_era}'"


def commodity_filter() -> str:
    if selected_commodity == "All":
        return "1=1"
    code = COMMODITY_MAP[selected_commodity]
    return f"commodity_type = '{code}'"


def combined_filter() -> str:
    return f"({era_filter()}) AND ({commodity_filter()})"


# ---------------------------------------------------------------------------
# Helper: run a query and return result
# ---------------------------------------------------------------------------

def q(sql: str):
    return get_con().execute(sql)


def fetch_df(sql: str):
    return q(sql).fetchdf()


def fetch_one(sql: str):
    return q(sql).fetchone()


# ---------------------------------------------------------------------------
# Page Title
# ---------------------------------------------------------------------------

st.title("Government of Canada Contracts - Analysis Dashboard")
st.caption(
    "Proactive disclosure of contracts over $10,000  |  "
    "National Defence excluded  |  Valid reporting periods only"
)

# ===================================================================
# Section 1: Dataset Overview
# ===================================================================

st.header("1. Dataset Overview")

f = combined_filter()

row_total = fetch_one(f"SELECT COUNT(*) FROM contracts WHERE {f}")[0]
unique_contracts = fetch_one(
    f"SELECT COUNT(DISTINCT procurement_id) FROM contracts WHERE {f} AND procurement_id IS NOT NULL"
)[0]
total_value = fetch_one(f"SELECT SUM(cv) FROM contracts WHERE {f}")[0] or 0
unique_vendors = fetch_one(
    f"SELECT COUNT(DISTINCT vendor_name) FROM contracts WHERE {f}"
)[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Rows", f"{row_total:,.0f}")
c2.metric("Unique Contracts", f"{unique_contracts:,.0f}")
c3.metric("Total Value", f"${total_value/1e9:,.1f}B")
c4.metric("Unique Vendors", f"{unique_vendors:,.0f}")

st.divider()

# ===================================================================
# Section 2: Insight 1 - Q4 Fiscal Year-End Spending Surge
# ===================================================================

st.header("2. Insight 1 - Q4 Fiscal Year-End Spending Surge")

st.markdown(
    "Canada's fiscal year ends March 31. Departments rush to spend remaining "
    "budgets in Q4 (January-March), creating a measurable spike in both contract "
    "count and average value."
)

# --- Chart 2a: Contract count by quarter (Q4 highlighted red) ---

qtr_counts = fetch_df(f"""
    SELECT quarter,
           COUNT(*) AS cnt
    FROM contracts
    WHERE {f}
    GROUP BY quarter
    ORDER BY quarter
""")

if not qtr_counts.empty:
    labels = {"Q1": "Q1 (Apr-Jun)", "Q2": "Q2 (Jul-Sep)",
              "Q3": "Q3 (Oct-Dec)", "Q4": "Q4 (Jan-Mar)"}
    qtr_counts["label"] = qtr_counts["quarter"].map(labels)
    colors = [BLUE if q != "Q4" else RED for q in qtr_counts["quarter"]]

    fig_qtr = go.Figure(go.Bar(
        x=qtr_counts["label"],
        y=qtr_counts["cnt"],
        marker_color=colors,
        text=qtr_counts["cnt"].apply(lambda v: f"{v:,.0f}"),
        textposition="outside",
    ))
    fig_qtr.update_layout(
        title="Contract Count by Quarter (Q4 highlighted)",
        yaxis_title="Number of Contracts",
        xaxis_title="Quarter",
        template="plotly_white",
        height=420,
    )
    st.plotly_chart(fig_qtr, use_container_width=True)

# --- Chart 2b: Q4 avg value vs Q1-Q3 avg value by commodity type ---

comm_q4 = fetch_df(f"""
    WITH base AS (
        SELECT commodity_type,
               quarter,
               cv
        FROM contracts
        WHERE {f}
          AND commodity_type IN ('S','G','C')
          AND cv IS NOT NULL AND cv > 0
    )
    SELECT commodity_type,
           AVG(CASE WHEN quarter = 'Q4' THEN cv END) AS q4_avg,
           AVG(CASE WHEN quarter != 'Q4' THEN cv END) AS q1q3_avg
    FROM base
    GROUP BY commodity_type
    ORDER BY commodity_type
""")

if not comm_q4.empty:
    comm_labels = {"C": "Construction", "G": "Goods", "S": "Services"}
    comm_q4["label"] = comm_q4["commodity_type"].map(comm_labels)
    comm_q4["ratio"] = comm_q4["q4_avg"] / comm_q4["q1q3_avg"]

    fig_comm = go.Figure()
    fig_comm.add_trace(go.Bar(
        name="Q1-Q3 Avg",
        x=comm_q4["label"],
        y=comm_q4["q1q3_avg"],
        marker_color=BLUE,
        text=comm_q4["q1q3_avg"].apply(lambda v: f"${v/1e3:,.0f}K"),
        textposition="outside",
    ))
    fig_comm.add_trace(go.Bar(
        name="Q4 Avg",
        x=comm_q4["label"],
        y=comm_q4["q4_avg"],
        marker_color=RED,
        text=comm_q4["q4_avg"].apply(lambda v: f"${v/1e3:,.0f}K"),
        textposition="outside",
    ))
    fig_comm.update_layout(
        barmode="group",
        title="Q4 Average Contract Value vs Q1-Q3 Average by Commodity Type",
        yaxis_title="Average Contract Value ($)",
        template="plotly_white",
        height=420,
    )
    # Add ratio annotations
    for _, row in comm_q4.iterrows():
        if row["q1q3_avg"] and row["q1q3_avg"] > 0:
            fig_comm.add_annotation(
                x=row["label"],
                y=max(row["q4_avg"], row["q1q3_avg"]) * 1.15,
                text=f"{row['ratio']:.2f}x",
                showarrow=False,
                font=dict(size=13, color=RED),
            )
    st.plotly_chart(fig_comm, use_container_width=True)

# --- Chart 2c: Q4 concentration by instrument type ---

inst_q4 = fetch_df(f"""
    SELECT instrument_type,
           COUNT(*) AS total,
           SUM(CASE WHEN quarter = 'Q4' THEN 1 ELSE 0 END) AS q4_count,
           ROUND(100.0 * SUM(CASE WHEN quarter = 'Q4' THEN 1 ELSE 0 END) / COUNT(*), 1) AS q4_pct
    FROM contracts
    WHERE {f}
      AND instrument_type IN ('A','C','SOSA')
    GROUP BY instrument_type
    ORDER BY q4_pct DESC
""")

if not inst_q4.empty:
    inst_labels = {"A": "Amendments", "C": "Contracts", "SOSA": "Standing Offers"}
    inst_q4["label"] = inst_q4["instrument_type"].map(inst_labels)
    bar_colors = [ORANGE if p > 27 else BLUE for p in inst_q4["q4_pct"]]

    fig_inst = go.Figure(go.Bar(
        x=inst_q4["label"],
        y=inst_q4["q4_pct"],
        marker_color=bar_colors,
        text=inst_q4["q4_pct"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
    ))
    fig_inst.update_layout(
        title="Q4 Concentration by Instrument Type (expected: 25%)",
        yaxis_title="% of Rows in Q4",
        template="plotly_white",
        height=400,
    )
    fig_inst.add_hline(y=25, line_dash="dash", line_color=GRAY,
                       annotation_text="Expected 25%", annotation_position="top left")
    st.plotly_chart(fig_inst, use_container_width=True)

# --- Chart 2d: Year-over-year Q4 vs Q1-Q3 average contract value ---

yoy = fetch_df(f"""
    SELECT fiscal_year,
           AVG(CASE WHEN quarter = 'Q4' THEN cv END) AS q4_avg,
           AVG(CASE WHEN quarter != 'Q4' THEN cv END) AS q1q3_avg
    FROM contracts
    WHERE {f}
      AND cv IS NOT NULL AND cv > 0
      AND fiscal_year != '2018-2018'
    GROUP BY fiscal_year
    HAVING COUNT(*) > 100
    ORDER BY fiscal_year
""")

if not yoy.empty:
    fig_yoy = go.Figure()
    fig_yoy.add_trace(go.Scatter(
        x=yoy["fiscal_year"], y=yoy["q1q3_avg"],
        mode="lines+markers", name="Q1-Q3 Avg",
        line=dict(color=BLUE, width=2),
        marker=dict(size=6),
    ))
    fig_yoy.add_trace(go.Scatter(
        x=yoy["fiscal_year"], y=yoy["q4_avg"],
        mode="lines+markers", name="Q4 Avg",
        line=dict(color=RED, width=2),
        marker=dict(size=6),
    ))
    fig_yoy.update_layout(
        title="Year-over-Year: Q4 vs Q1-Q3 Average Contract Value",
        yaxis_title="Average Contract Value ($)",
        xaxis_title="Fiscal Year",
        template="plotly_white",
        height=420,
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig_yoy, use_container_width=True)

st.markdown("""
**Key finding:** Q4 consistently has the highest contract count across all years.
Construction contracts show the largest Q4 surge, with Q4 average values reaching
up to 5.84x the Q1-Q3 average. Amendments are particularly concentrated in Q4
(~32.7%), well above the expected 25%.

**Recommendations:**
- Implement quarterly budget utilization monitoring to smooth spending across the year
- Flag Q4 contracts above a certain threshold for enhanced review
- Consider multi-year funding authorities to reduce "use it or lose it" incentives
""")

st.divider()

# ===================================================================
# Section 3: Insight 2 - Amendment Growth
# ===================================================================

st.header("3. Insight 2 - Amendment Growth")

st.markdown(
    "Amendments allow contracts to grow beyond their original value without "
    "re-competing. Nearly 1 in 4 rows is an amendment, and many contracts grow "
    "by multiples of their original value."
)

# --- Chart 3a: Amendment rate by fiscal year ---

amend_rate = fetch_df(f"""
    SELECT fiscal_year,
           COUNT(*) AS total,
           SUM(CASE WHEN instrument_type = 'A' THEN 1 ELSE 0 END) AS amendments,
           ROUND(100.0 * SUM(CASE WHEN instrument_type = 'A' THEN 1 ELSE 0 END) / COUNT(*), 1) AS amend_pct
    FROM contracts
    WHERE {f}
      AND fiscal_year != '2018-2018'
    GROUP BY fiscal_year
    HAVING COUNT(*) > 100
    ORDER BY fiscal_year
""")

if not amend_rate.empty:
    fig_ar = go.Figure(go.Bar(
        x=amend_rate["fiscal_year"],
        y=amend_rate["amend_pct"],
        marker_color=[ORANGE if p > 20 else BLUE for p in amend_rate["amend_pct"]],
        text=amend_rate["amend_pct"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
    ))
    fig_ar.update_layout(
        title="Amendment Rate by Fiscal Year",
        yaxis_title="Amendment Rate (%)",
        xaxis_title="Fiscal Year",
        template="plotly_white",
        height=420,
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig_ar, use_container_width=True)

# --- Chart 3b: Amendment growth distribution (horizontal bar) ---

growth_dist = fetch_df(f"""
    WITH amended AS (
        SELECT
            cv,
            ov,
            CASE WHEN ov > 0 THEN cv / ov ELSE NULL END AS growth_ratio
        FROM contracts
        WHERE {f}
          AND instrument_type = 'A'
          AND cv IS NOT NULL AND ov IS NOT NULL AND ov > 0
    )
    SELECT
        CASE
            WHEN growth_ratio <= 1.0 THEN 'Decreased or unchanged'
            WHEN growth_ratio <= 1.5 THEN '1x - 1.5x'
            WHEN growth_ratio <= 2.0 THEN '1.5x - 2x'
            WHEN growth_ratio <= 3.0 THEN '2x - 3x'
            WHEN growth_ratio <= 5.0 THEN '3x - 5x'
            WHEN growth_ratio <= 10.0 THEN '5x - 10x'
            ELSE '10x+'
        END AS bucket,
        COUNT(*) AS cnt,
        CASE
            WHEN growth_ratio <= 1.0 THEN 1
            WHEN growth_ratio <= 1.5 THEN 2
            WHEN growth_ratio <= 2.0 THEN 3
            WHEN growth_ratio <= 3.0 THEN 4
            WHEN growth_ratio <= 5.0 THEN 5
            WHEN growth_ratio <= 10.0 THEN 6
            ELSE 7
        END AS sort_order
    FROM amended
    GROUP BY bucket, sort_order
    ORDER BY sort_order
""")

if not growth_dist.empty:
    growth_colors = [GREEN, GREEN, BLUE, ORANGE, ORANGE, RED, RED]
    # Trim to actual number of buckets
    growth_colors = growth_colors[:len(growth_dist)]

    fig_gd = go.Figure(go.Bar(
        y=growth_dist["bucket"],
        x=growth_dist["cnt"],
        orientation="h",
        marker_color=growth_colors,
        text=growth_dist["cnt"].apply(lambda v: f"{v:,.0f}"),
        textposition="outside",
    ))
    fig_gd.update_layout(
        title="Amendment Growth Distribution (contract_value / original_value)",
        xaxis_title="Number of Amendments",
        yaxis_title="Growth Ratio",
        template="plotly_white",
        height=420,
    )
    st.plotly_chart(fig_gd, use_container_width=True)

# --- Table 3c: Top 10 most-grown contracts ---

st.subheader("Top 10 Most-Grown Contracts")

top_grown = fetch_df(f"""
    WITH latest AS (
        SELECT
            procurement_id,
            vendor_name,
            SPLIT_PART(owner_org_title, ' | ', 1) AS dept,
            cv AS final_value,
            ov AS original_value,
            CASE WHEN ov > 0 THEN ROUND(100.0 * (cv - ov) / ov, 1) ELSE NULL END AS growth_pct,
            ROW_NUMBER() OVER (
                PARTITION BY procurement_id
                ORDER BY cv DESC
            ) AS rn
        FROM contracts
        WHERE {f}
          AND instrument_type = 'A'
          AND cv IS NOT NULL AND ov IS NOT NULL AND ov > 0
          AND procurement_id IS NOT NULL
    )
    SELECT
        procurement_id,
        vendor_name AS vendor,
        dept,
        ROUND(original_value / 1e6, 2) AS original_M,
        ROUND(final_value / 1e6, 2) AS final_M,
        growth_pct
    FROM latest
    WHERE rn = 1
    ORDER BY (final_value - original_value) DESC
    LIMIT 10
""")

if not top_grown.empty:
    display_df = top_grown.copy()
    display_df.columns = [
        "Procurement ID", "Vendor", "Department",
        "Original ($M)", "Final ($M)", "Growth %"
    ]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- Chart 3d: Amendment rate by commodity type ---

amend_comm = fetch_df(f"""
    SELECT
        commodity_type,
        COUNT(*) AS total,
        SUM(CASE WHEN instrument_type = 'A' THEN 1 ELSE 0 END) AS amendments,
        ROUND(100.0 * SUM(CASE WHEN instrument_type = 'A' THEN 1 ELSE 0 END) / COUNT(*), 1) AS amend_pct
    FROM contracts
    WHERE {f}
      AND commodity_type IN ('S','G','C')
    GROUP BY commodity_type
    ORDER BY amend_pct DESC
""")

if not amend_comm.empty:
    comm_labels_map = {"C": "Construction", "G": "Goods", "S": "Services"}
    amend_comm["label"] = amend_comm["commodity_type"].map(comm_labels_map)

    fig_ac = go.Figure(go.Bar(
        x=amend_comm["label"],
        y=amend_comm["amend_pct"],
        marker_color=[ORANGE if p > 20 else BLUE for p in amend_comm["amend_pct"]],
        text=amend_comm["amend_pct"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
    ))
    fig_ac.update_layout(
        title="Amendment Rate by Commodity Type",
        yaxis_title="Amendment Rate (%)",
        template="plotly_white",
        height=400,
    )
    st.plotly_chart(fig_ac, use_container_width=True)

st.markdown("""
**Key finding:** Amendment rates have risen from ~16% (pre-2019) to ~24.5% (post-2022).
40% of amendments more than double the original contract value. Construction contracts
have the highest amendment rate. Some contracts grow by 50x or more from their original
value, effectively bypassing the competitive process used for the original award.

**Recommendations:**
- Set automatic re-competition triggers when amendments exceed 200% of original value
- Require documented justification for amendments over a dollar threshold
- Track amendment patterns by department to identify systemic scoping issues
""")

st.divider()

# ===================================================================
# Section 4: Data Quality Notes
# ===================================================================

st.header("4. Data Quality Notes")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Vendor Name Inconsistency")
    st.markdown(
        "The same vendor appears under multiple spellings, making vendor-level "
        "analysis unreliable without normalization. Example:"
    )
    vendor_example = fetch_df("""
        SELECT vendor_name, COUNT(*) AS rows
        FROM contracts
        WHERE UPPER(vendor_name) LIKE '%CALIAN%'
        GROUP BY vendor_name
        ORDER BY rows DESC
        LIMIT 6
    """)
    if not vendor_example.empty:
        st.dataframe(vendor_example, use_container_width=True, hide_index=True)

with col_b:
    st.subheader("Malformed Reporting Periods")
    malformed_count = fetch_one("""
        SELECT COUNT(*) FROM raw
        WHERE reporting_period IS NOT NULL
          AND reporting_period NOT LIKE '____-____-Q_'
          AND owner_org_title NOT LIKE 'National Defence%'
    """)[0]
    st.metric("Rows with invalid reporting_period", f"{malformed_count:,}")
    st.markdown(
        'Examples: `"C"`, `"2010-11-Q4"`, `"2018/2019/Q3"`, `"Q1"`, `"2108-2019"`. '
        "These are excluded from all analysis above."
    )

st.subheader("Three Reporting Eras")
st.markdown("""
The Government of Canada changed mandatory reporting requirements at two key dates,
creating three eras with different data quality:

| Era | Period | What changed |
|---|---|---|
| **Pre-2019** | Before 2019-01-01 | Minimal mandatory fields - most reporting voluntary |
| **2019-2022** | 2019-01-01 to 2021-12-31 | Core fields mandatory (vendor name, values, commodity type) |
| **Post-2022** | 2022-01-01 onward | Near-complete reporting (solicitation, trade agreements, Indigenous business) |

Cross-era comparisons must account for this - apparent changes may reflect better
reporting, not actual behaviour shifts. The sidebar era filter lets you isolate
each period.
""")

st.markdown("""
**Minor finding - vendor name duplicates:** Common patterns include trailing periods
("Irving Shipbuilding Inc" vs "Irving Shipbuilding Inc."), case differences
("CALIAN LTD." vs "Calian Ltd"), and abbreviation variants. Any vendor
concentration analysis would need fuzzy matching or normalization as a prerequisite.
""")

st.divider()

# ===================================================================
# Section 5: What I'd Investigate Next
# ===================================================================

st.header("5. What I'd Investigate Next")

st.markdown("""
- **Vendor name deduplication** - Apply fuzzy matching (e.g. Levenshtein distance,
  phonetic matching) to normalize the 208,000+ vendor names and reveal true
  concentration metrics. The same vendor likely appears under dozens of spellings.

- **Sole-source justification gap** - 68,921 non-competitive contracts list "None"
  as the limited tendering reason. While technically compliant when no trade agreement
  applies, this represents a transparency gap worth auditing.

- **COVID procurement persistence** - Public Health Agency spending surged 49x during
  2020-2021. Post-COVID spending has not returned to baseline, suggesting pandemic-era
  procurement norms (faster, less competitive) became entrenched. Worth comparing to
  municipal pandemic spending patterns.

- **Halton-specific benchmarking** - Vendors in the L6/L7 postal code area hold
  $10B+ in federal contracts. Cross-referencing Halton Region's own procurement
  data against federal norms for similar categories (IT, facilities, construction)
  could identify opportunities and risks.
""")

st.divider()

st.caption(
    "Built with Streamlit, DuckDB, and Plotly  |  "
    "Data source: Government of Canada Proactive Disclosure of Contracts Over $10,000  |  "
    "Analysis by Ayman Tauhid"
)
