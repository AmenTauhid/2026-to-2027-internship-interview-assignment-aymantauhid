# A Self-Reinforcing Cycle in Federal Procurement

- Year-end budget pressure leads to rushed contracts
- Those contracts grow through amendments
- A small group of vendors benefits disproportionately, reinforcing the cycle

1.26M rows of Government of Canada procurement data (excl. National Defence) reveal the pattern.

---

## What is this dataset?

1.26 million rows of federal contract data spanning fiscal years 2004-2025, covering 99 government departments and 208,000+ vendors. Each row is a **transaction** - a new contract, an amendment, or a standing offer - not a unique contract. The `procurement_id` field links a contract to its amendments.

**Scope decisions for this analysis:**
- National Defence excluded (structurally different procurement - shipbuilding, fighter jets - skews all civilian patterns)
- Only rows with valid `reporting_period` format (filters out ~2,600 malformed entries)
- Three reporting eras analyzed separately where field availability differs

---

## Data quality, limitations, and assumptions

### Data completeness

- **Pre-2019**: Voluntary reporting. `commodity_type`, `instrument_type` not mandatory. Volume counts inflated.
- **Post-2019**: Mandatory reporting. Core fields reliable. Primary evidence base.

### Data quality issues encountered

1. **Malformed `reporting_period`**: ~2,600 rows with values like "C", "Q1", "2010-11-Q4", "2108-2019". Excluded using `LIKE '____-____-Q_'` filter.
2. **Vendor name inconsistency**: Same vendor appears under multiple spellings (case, periods, abbreviations). "Canadian Corps of Commissionaires" has 10+ variants totaling 10,000+ rows. Vendor concentration metrics likely understate true concentration.
3. **`reporting_period` is reporting date, not award date**: Records when a contract was disclosed, not when it was awarded. Only mandatory after 2019-01-01. Q4 patterns could partially reflect reporting lag, but the pattern is too large and consistent to be explained by lag alone.
4. **All columns load as VARCHAR**: Financial fields require explicit casting. Zero cast failures across all 1.26M rows.
5. **28% of rows have no `instrument_type`**: Older records before the field was mandatory. Excluded from contract/amendment analysis.

### Assumptions

- Vendor names used as-is without normalization - concentration is conservatively estimated
- `contract_value` on amendment rows = cumulative running total, not incremental amount
- National Defence excluded (structurally different procurement)
- All values nominal CAD, not inflation-adjusted

---

## Insight 1: Fiscal year-end (Q4) spending surge

### The pattern

- Q4 sees 20% more procurement activity post-2019
- Construction contracts average 5.84x higher in Q4 (post-2019)
- Amendments more concentrated in Q4 (32.7%) than new contracts (27.5%)
- Sole-source rate higher in Q4 (41.3% vs 39.1%)

### Why it matters

- 'Use it or lose it' budget behaviour
- Departments rush to spend before March 31 or risk losing next year's budget
- Leads to less competition, oversized awards, and poorly scoped contracts
- Sets up the amendment growth in Insight 2

### What to do

- Q3 early warning: alert departments whose Q1-Q3 spending is low relative to budget - they will likely surge in Q4
- Flag high-value Q4 construction contracts for additional review
- Track Q4 sole-source rates by department
- Consider multi-year budgeting for recurring needs

### Caveat

`reporting_period` records when a contract was *reported*, not when it was *awarded*. The pattern is too large and consistent to be explained by reporting lag alone.

---

## Insight 2: Contracts grow significantly through amendments

### The pattern

- ~25% of all rows are amendments post-2019
- Services: 31.4% amendment rate
- Amendments spike in Q4 (28.2% vs 23.3%)
- Some contracts grow from $18.6M to $1B through 16 amendments

### By commodity type (post-2019)

| Commodity | Amendment rate | Median growth | P95 growth |
|---|---|---|---|
| Services | 31.4% | 36% | 371% |
| Construction | 30.4% | 15% | 155% |
| Goods | 9.0% | 9% | 232% |

### By solicitation procedure (post-2019)

- **Competitive contracts: 26.2% amendment rate**
- **Sole-source contracts: 14.3% amendment rate**
- Competitive contracts get amended nearly twice as often - consistent with vendors bidding low to win, then expanding through amendments

### Top departments by amendment rate (post-2019)

| Department | Amendment rate |
|---|---|
| Canada Revenue Agency | 51.0% |
| IRCC | 46.7% |
| ESDC | 44.8% |
| PSPC | 40.2% |

### Dollar scale (post-2019)

- 44,030 contracts were amended
- Original total: $29.1B
- Final total: $42.5B
- **$13.4B added through amendments** (46% growth without re-competing)

### Extreme examples (excl. Defence)

| Vendor | Department | Original | Final | Growth |
|---|---|---|---|---|
| BGIS Global Integrated Solutions | PSPC | $338.0M | $2.49B | +638% |
| Bell Mobility | Shared Services Canada | $18.6M | $1.04B | +5,495% |
| Parsons Inc | PSPC | $49.8M | $1.69B | +3,302% |
| Vancouver Shipyards | Fisheries and Oceans | $179.9M | $1.07B | +495% |
| Ellisdon Corporation | PSPC | $40K | $623.4M | +1,558,436% |

### Why it matters

- Massive growth effectively bypasses the original competitive process
- Q4-rushed contracts are more likely to need scope changes later
- Creates a pipeline from budget pressure to uncompeted growth

### What to do

- Set amendment thresholds (e.g., re-compete at 50% growth)
- Separate routine from material amendments by size
- Focus oversight on services (highest growth risk)
- Monitor Q4 amendments as a compounding risk

### Caveat

Growth estimated by comparing `MAX(contract_value)` to `MIN(original_value)` across rows sharing a `procurement_id`. Some amendment rows include restatements/corrections, not just scope expansion.

---

## Insight 3: Spending is concentrated in a few vendors - and they get amended more

### The pattern

- Top 50 vendors (out of 126,000+) hold 55% of all spend
- Their amendment rate is 38% - nearly double the 21% for others
- 18 departments have >30% of spend with a single vendor

### Vendor concentration

| Vendor Group | % of Total Spend |
|---|---|
| Top 10 vendors | 28.7% |
| Top 50 vendors | 55.0% |
| Top 100 vendors | 62.6% |
| Top 500 vendors | 79.5% |
| Remaining 125,969 vendors | 20.5% |

### Single-vendor dependency

| Department | Top Vendor | % of Dept Spend |
|---|---|---|
| Dept. of Housing & Infrastructure | Groupe Signature sur le | 40.1% |
| Canadian Space Agency | MDA Systems | 39.0% |
| Fisheries and Oceans | Vancouver Shipyards | 38.6% |
| Treasury Board | Sun Life Assurance | 38.3% |
| Canada Border Services | Deloitte Inc | 31.1% |
| Employment & Social Dev | D+H Corporation | 28.8% |

### Why it matters

- Vendor lock-in reduces negotiating leverage and creates supply chain risk
- Biggest vendors benefit from both the initial award and scope expansion
- Completes the cycle: Q4 rush, amendment growth, vendor concentration

### What to do

- Map vendor dependency for critical services
- Flag departments where one vendor holds >30% of spend
- Diversify vendor base for recurring contract categories
- Monitor whether top-vendor contracts are amended at higher rates

### Caveat

Vendor names are not normalized. Same vendor can appear under multiple spellings. True vendor concentration is likely higher than reported.

---

## Federal benchmarks

| Metric | Benchmark |
|---|---|
| Q4 volume surge | +20% (post-2019) to +38% (all years) |
| Q4 share of contract value | 34.8% all years, 35.4% post-2019 (expected: 25%) |
| Q4 construction value multiplier | 3.4x (all years), 5.84x (post-2019) |
| Q4 sole-source rate vs Q1-Q3 | 41.3% vs 39.1% (post-2019) |
| Q4 share of amendments | 32.7% (vs 27.5% for new contracts, post-2019) |
| Amendment rate | ~25% (post-2019) |
| Competitive vs sole-source amendment rate | 26.2% vs 14.3% (post-2019) |
| $ added through amendments | $13.4B (post-2019) |
| Top 50 vendor share of spend | 55% |
| Top 50 vendor amendment rate | 37.7% (vs 20.5% for others) |
| Departments with >30% single-vendor dependency | 18 out of 97 |

---

## What I'd investigate next

1. **Test the causal chain: Q4 rush to amendments**
   - Are contracts *awarded* in Q4 amended more in later quarters?
   - Would confirm that year-end rush causes poorly scoped contracts
   - Direct causal link between Insight 1 and Insight 2

2. **Do top vendors bid low and grow through amendments?**
   - Compare original vs. final values by vendor tier
   - If top vendors consistently win low and grow high, it suggests strategic low-bidding
   - Would inform bid evaluation criteria

3. **Department-level risk scores**
   - Combine Q4 surge, amendment rate, and vendor concentration into one score per department
   - Identifies which departments have the worst combination of all three risks
   - Prioritizes oversight where it matters most

4. **Local economic intelligence - the Halton share**
   - Filter `vendor_postal_code` (mandatory post-2019) by Halton prefixes (L6, L7, L9)
   - Identify how much federal contract money flows into Oakville, Burlington, Milton, Halton Hills
   - Reveal which local industries are winning federal business
   - Give Economic Development concrete data to attract similar companies

---

## Technical approach

| Phase | Notebook | Purpose |
|---|---|---|
| 1 | `phase1-exploration.ipynb` | Understand the dataset: size, grain, columns, missing data, time range |
| 2 | `phase2-profiling.ipynb` | Profile key fields, follow threads, decide which patterns to investigate |
| 3 | `phase3-analysis.ipynb` | Deep-dive into three insights with evidence, charts, and recommendations |

**Tools used**: DuckDB (SQL queries), Polars (DataFrames), Plotly (interactive charts), Python, Data Wrangler (Microsoft VS Code extension for initial data profiling), Streamlit (interactive dashboard)

**Key technical decisions**:
- Used Data Wrangler for initial column profiling and quick visual inspection of data types, nulls, and distributions before writing queries
- Loaded all columns as VARCHAR to avoid type-guessing issues, cast manually with TRY_CAST
- Created a reusable SQL view excluding Defence and filtering to valid reporting periods
- Analyzed three eras separately where field availability differs
- Used `ROLLUP` for overall-vs-era comparisons in a single query
