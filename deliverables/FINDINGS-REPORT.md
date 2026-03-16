# Government of Canada Contracts Over $10,000 - Findings Report

## What is this dataset?

1.26 million rows of federal contract data spanning fiscal years 2004-2025, covering 99 government departments and 208,000+ vendors. Each row is a **transaction** - a new contract, an amendment, or a standing offer - not a unique contract. The `procurement_id` field links a contract to its amendments.

**Scope decisions for this analysis:**
- National Defence excluded (structurally different procurement - shipbuilding, fighter jets - skews all civilian patterns)
- Only rows with valid `reporting_period` format (filters out ~2,600 malformed entries)
- Three reporting eras analyzed separately where field availability differs

---

## Data quality, limitations, and assumptions

### Three reporting eras

Mandatory field requirements expanded over time. This directly affects what comparisons are valid.

| Era | What became mandatory | Impact on this analysis |
|---|---|---|
| Pre-2019 | Only `reference_number` | 35-97% missing on process fields. Pre-2019 quarterly and solicitation data is incomplete - patterns may reflect missing data, not actual behaviour. |
| 2019-2022 | Core fields: `procurement_id`, `contract_value`, `commodity_type`, `instrument_type` | Core financial data reliable. Amendment and Q4 analysis most trustworthy from this era onward. |
| Post-2022 | Process fields: `solicitation_procedure`, `vendor_postal_code`, `contracting_entity` | Most complete data. Where possible, post-2019 or post-2022 numbers are used. |

### Data quality issues encountered

1. **Malformed `reporting_period`**: ~2,600 rows with values like "C", "Q1", "2010-11-Q4", "2108-2019". **Decision**: excluded from all time-based analysis using `LIKE '____-____-Q_'` filter.
2. **Vendor name inconsistency**: Same vendor appears under multiple spellings (case, periods, abbreviations). "Canadian Corps of Commissionaires" has 10+ variants totaling 10,000+ rows. **Impact**: vendor concentration metrics (Insight 3) likely understate true concentration.
3. **`reporting_period` is reporting date, not award date**: This field records when a contract was disclosed to the public, not when it was awarded. Only mandatory after 2019-01-01. **Impact**: Q4 patterns (Insight 1) could partially reflect reporting lag. However, the pattern is too large and consistent to be explained by lag alone.
4. **All columns load as VARCHAR**: Financial fields (`contract_value`, `original_value`, `amendment_value`) require explicit casting. Zero cast failures across all 1.26M rows - financial data is clean.
5. **28% of rows have no `instrument_type`**: These are older records before the field was mandatory. **Decision**: excluded from any analysis that depends on distinguishing contracts from amendments.

### Assumptions

- **Vendor names used as-is** without fuzzy matching or normalization. This means vendor concentration is conservatively estimated - the real concentration is higher.
- **`contract_value` on amendment rows represents the cumulative running total**, not the incremental amendment amount. This is how we estimate contract growth (comparing max `contract_value` to min `original_value` within a `procurement_id`).
- **National Defence excluded** because its procurement (shipbuilding, fighter jets, armoured vehicles) is structurally different and would dominate every metric. All numbers in this report are civilian departments only.
- **All values are nominal CAD** - not adjusted for inflation. Real growth over time would be somewhat lower than the nominal figures shown.

---

## Insight 1: Fiscal year-end (Q4) spending surge

*Scope: excl. Defence, valid reporting periods only. Volume uses all transaction types. Value uses new contracts only (amendment values are cumulative totals, not new spending).*

### The pattern

Canada's fiscal year ends March 31. Q4 (January-March) shows a clear year-end surge:

**Volume** (all transaction types - contracts, amendments, SOSAs):
- **38% more procurement activity** in Q4 than the Q1-Q3 average (257,055 vs 185,671 avg)

**Value** (new contracts only - the only clean measure of new spending):
- Q4 average contract value is **$215K vs $177K** in Q1-Q3
- **34.8% of total contract value** lands in Q4 (expected: 25% if evenly distributed)

### Two channels

The rush operates through both new awards and scope expansion on existing contracts (post-2019, where reporting is mandatory):
- **New contracts**: 27.5% fall in Q4 (expected: 25%)
- **Amendments**: 32.7% fall in Q4 - even more concentrated than new awards

The non-competitive (sole-source) rate is also higher in Q4: 41.3% vs 39.1% in Q1-Q3 (post-2019, contracts only).

### Construction hit hardest

In the post-2019 data, Q4 construction contracts average **5.84x** higher than other quarters ($1.56M vs $267K). Services show a modest 1.13x bump. Goods barely differ (1.02x).

### Era comparison (contracts only)

| Era | Q4 value multiplier | Notes |
|---|---|---|
| Pre-2019 | 0.91x | No Q4 value surge (but `reporting_period` was not mandatory - data is incomplete) |
| 2019-2022 | 1.04x | Slight Q4 premium |
| Post-2022 | 1.89x | Strong and intensifying |

The Q4 pattern is modern and growing. The pre-2019 absence likely reflects incomplete data rather than different behaviour, since `reporting_period` was not mandatory before 2019.

### Recommendations

- Flag high-value Q4 construction contracts for additional review
- Track Q4 sole-source and amendment rates by department on a quarterly dashboard
- Consider multi-year budgeting for recurring needs to reduce the year-end rush

### Caveat

`reporting_period` records when a contract was *reported*, not when it was *awarded*. Some Q4 entries may be backlog from earlier quarters. The pattern is too large and consistent to be explained by reporting lag alone.

---

## Insight 2: Contracts grow significantly through amendments

### The pattern

- **1 in 4 transaction rows is an amendment** (up from 1 in 6 pre-2019)
- Overall amendment rate: 23.3%. Post-2019: ~25%
- Of amended contracts: **40% more than double in value**, 10.5% grow by **500%+**

### By commodity type

| Commodity | Amendment rate (post-2022) | Median growth | % that more than double |
|---|---|---|---|
| Services | 31.8% | 38% | 28.2% |
| Construction | 28.5% | 16% | 8.2% |
| Goods | 8.5% | 12% | 17.3% |

Services are the highest-risk category - they're amended most often, grow the most, and the rate is increasing (28.9% pre-2019 to 31.7% post-2022). Construction has a similar amendment rate but amendments tend to be smaller. Construction's rate actually *decreased* over time (32.6% to 28.5%). Goods are rarely amended.

### Extreme examples (excl. Defence)

| Vendor | Department | Original | Final | Growth |
|---|---|---|---|---|
| BGIS Global Integrated Solutions | PSPC | $338.0M | $2.49B | +638% |
| Bell Mobility | Shared Services Canada | $18.6M | $1.04B | +5,495% |
| Parsons Inc | PSPC | $49.8M | $1.69B | +3,302% |
| Vancouver Shipyards | Fisheries and Oceans | $179.9M | $1.07B | +495% |
| Ellisdon Corporation | PSPC | $40K | $623.4M | +1,558,436% |

### Connection to Q4

The amendment rate is higher in Q4 (25.7% of Q4 rows are amendments vs 22.2% in Q1-Q3). Year-end pressure drives both new awards and scope expansion on existing contracts.

### Recommendations

- Set amendment thresholds - if cumulative amendments exceed 50% of original value, require documented justification or re-compete
- Separate routine amendments (small extensions) from material ones (scope changes) by size relative to original value
- Track amendment rates by commodity type - services need the most oversight, not construction as might be assumed
- Watch Q4 amendments specifically - year-end pressure drives both channels

### Caveat

We estimate growth by comparing `MAX(contract_value)` to `MIN(original_value)` across rows sharing a `procurement_id`. This depends on consistent reporting across amendment entries.

---

## Insight 3: Spending is concentrated in a few vendors - and they get amended more

### The pattern

Out of 126,000+ vendors (excl. Defence), spending is heavily concentrated:

| Vendor Group | % of Total Spend |
|---|---|
| Top 10 vendors | 28.7% |
| Top 50 vendors | 55.0% |
| Top 100 vendors | 62.6% |
| Top 500 vendors | 79.5% |
| Remaining 125,969 vendors | 20.5% |

### The connection to amendments

This is what makes vendor concentration more than a descriptive statistic. Top vendors don't just win more work - their contracts grow more through amendments:

| Vendor Tier | Amendment Rate |
|---|---|
| Top 50 vendors | **37.7%** |
| All other vendors | 20.5% |

Top vendors have nearly double the amendment rate. This links directly to Insight 2: the biggest vendors benefit the most from the amendment culture, creating a self-reinforcing cycle.

### Single-vendor dependency

18 out of 97 departments have more than 30% of their entire spend with a single vendor. The most extreme cases:

| Department | Top Vendor | % of Dept Spend |
|---|---|---|
| Dept. of Housing & Infrastructure | Groupe Signature sur le | 40.1% |
| Canadian Space Agency | MDA Systems | 39.0% |
| Fisheries and Oceans | Vancouver Shipyards | 38.6% |
| Treasury Board | Sun Life Assurance | 38.3% |
| Canada Border Services | Deloitte Inc | 31.1% |
| Employment & Social Dev | D+H Corporation | 28.8% |
| Shared Services Canada | IBM Canada | 21.9% |

### Recommendations

- Map vendor dependency for critical services - flag any department where one vendor holds >30% of spend
- Diversify vendor base for recurring contract categories
- Monitor whether top-vendor contracts are growing disproportionately through amendments
- Consider vendor name normalization as a data quality initiative - true concentration is likely even higher than reported

### Caveat

Vendor names are not normalized. The same vendor can appear under multiple spellings (e.g., "Canadian Corps of Commissionaires" has 10+ variants across 10,200+ rows). True vendor concentration is likely higher than these numbers suggest.

---

## How the insights connect

These aren't three separate problems. They're a self-reinforcing cycle.

**Q4 pressure** drives a rush of contract awards and amendments at fiscal year-end. **Amendment growth** expands contracts far beyond their original scope - 40% of amended contracts more than double. And **vendor concentration** means the biggest vendors benefit the most from this cycle, with amendment rates nearly double the rest of the market (38% vs 21%).

The cycle works like this: year-end budget pressure creates rushed awards. Those awards go disproportionately to established vendors. Those vendors' contracts then grow through amendments, concentrating even more spending with the same firms. The result is a procurement system where the competitive process used for the original award becomes less meaningful over time.

### Federal benchmarks

| Metric | Benchmark | Scope |
|---|---|---|
| Q4 volume surge (all transaction types) | +38% vs Q1-Q3 average | All types, all eras |
| Q4 share of total contract value | 34.8% (expected: 25%) | Contracts only, all eras |
| Q4 avg contract value vs Q1-Q3 | $215K vs $177K | Contracts only, all eras |
| Q4 construction value multiplier | 5.84x | Contracts only, post-2019 |
| Q4 sole-source rate vs Q1-Q3 | 41.3% vs 39.1% | Contracts only, post-2019 |
| Q4 share of new contracts | 27.5% | Post-2019 |
| Q4 share of amendments | 32.7% | Post-2019 |
| Amendment rate | ~25% | Post-2019 |
| Services amendment rate | 31.4% | Post-2019 |
| Top 50 vendor share of total spend | 55% | All eras, excl. Defence |
| Top 50 vendor amendment rate | 37.7% (vs 20.5% for others) | All eras, excl. Defence |
| Departments with >30% single-vendor dependency | 18 out of 97 | All eras, excl. Defence |

These are numbers any government procurement office can compare against.

---

## Minor finding: vendor name inconsistency

The same vendor appears under different spellings throughout the dataset. Examples:

| Variant 1 | Variant 2 | Combined rows |
|---|---|---|
| CANADIAN CORPS OF COMMISSIONAIRES | Canadian Corps of Commissionaires | 10,200+ |
| STANTEC CONSULTING LTD. | Stantec Consulting Ltd. | 4,500+ |
| NISHA TECHNOLOGIES INC. | Nisha Technologies Inc. | 5,100+ |

This is a data engineering issue, not an analytical insight. But it means any vendor-level analysis (concentration, total awards) will undercount true concentration until names are normalized.

---

## What I'd investigate next

1. **Do Q4 contracts get amended more than Q1-Q3 contracts?** We showed amendments are more common *in* Q4, but are contracts *awarded* in Q4 more likely to be amended later? That would confirm the "rushed award, expanded later" hypothesis.

2. **Which specific contract descriptions drive the Q4 volume surge?** Are certain categories (e.g., temporary help, consulting) disproportionately rushed at year-end? Knowing the category would sharpen the recommendation.

3. **Vendor name normalization** - fuzzy matching vendor names would reveal the true concentration, which is likely even more extreme than reported here.

4. **Do top vendors bid low and grow through amendments?** Comparing original award values to final values by vendor tier could reveal whether strategic low-bidding is a pattern.

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
