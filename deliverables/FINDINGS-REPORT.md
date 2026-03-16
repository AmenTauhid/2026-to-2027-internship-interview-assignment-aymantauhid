# Government of Canada Contracts Over $10,000 - Findings Report

## What is this dataset?

1.26 million rows of federal contract data spanning fiscal years 2004-2025, covering 99 government departments and 208,000+ vendors. Each row is a **transaction** - a new contract, an amendment, or a standing offer - not a unique contract. The `procurement_id` field links a contract to its amendments.

**Scope decisions for this analysis:**
- National Defence excluded (structurally different procurement - shipbuilding, fighter jets - skews all civilian patterns)
- Only rows with valid `reporting_period` format (filters out ~2,800 malformed entries)
- Three reporting eras analyzed separately where field availability differs

---

## Data quality and limitations

### Three reporting eras

Mandatory field requirements expanded over time. This matters because cross-era comparisons can be misleading.

| Era | What became mandatory | Impact |
|---|---|---|
| Pre-2019 | Only `reference_number` | 35-97% missing on process fields |
| 2019-2022 | Core fields: `procurement_id`, `contract_value`, `commodity_type`, `instrument_type` | Core financial data reliable |
| Post-2022 | Process fields: `solicitation_procedure`, `vendor_postal_code`, `contracting_entity` | Most complete data |

### Data quality issues found

1. **Malformed reporting_period**: ~2,800 rows with values like "C", "Q1", "2010-11-Q4", "2108-2019". Excluded from time-based analysis.
2. **Vendor name inconsistency**: Same vendor under multiple spellings (case, periods, abbreviations). "Canadian Corps of Commissionaires" appears under 3+ variants with 7,000+ rows combined. Vendor-level counts may undercount true concentration.
3. **`reporting_period` records when a contract was reported to the public, not when it was awarded.** Only mandatory after 2019-01-01. This is a limitation for any time-based pattern analysis.
4. **All columns load as VARCHAR.** Financial fields (`contract_value`, `original_value`, `amendment_value`) require casting. Zero cast failures across all 1.26M rows.

### Assumptions

- Vendor names used as-is without normalization (insights don't depend on exact vendor matching)
- `contract_value` on amendment rows represents the running total, not the amendment amount
- SOSAs with $0 value are valid by design (frameworks, not spending)
- Negative `amendment_value` entries are legitimate (scope reductions)

---

## Insight 1: Fiscal year-end (Q4) spending surge

### The pattern

Canada's fiscal year ends March 31. Q4 (January-March) consistently shows:
- **32% more contracts** than the Q1-Q3 average
- **34.8% of total value** (expected: 25% if evenly distributed)
- **1.89x average contract value** compared to other quarters (post-2022)

### What's being rushed

Construction is hit hardest - Q4 average contract value is **5.84x higher** than other quarters ($1.56M vs $267K). Services show a modest 1.13x bump. Goods barely differ (1.02x).

### How it happens

The year-end rush operates through two channels:
- **New contracts**: 27.5% of all new contracts are in Q4
- **Amendments**: 32.7% of all amendments are in Q4 - even more concentrated than new awards

The non-competitive (sole-source) rate is also slightly higher in Q4: 41.3% vs 39.1% in Q1-Q3.

### Era comparison

| Era | Q4 value multiplier | Notes |
|---|---|---|
| Pre-2019 | 0.91x | No Q4 surge (but `reporting_period` was not mandatory) |
| 2019-2022 | 1.04x | Mild surge |
| Post-2022 | 1.89x | Strong and growing |

The pattern is modern and intensifying. The pre-2019 absence of a surge could reflect incomplete data rather than different behaviour.

### Recommendations

- Flag high-value Q4 construction and service contracts for additional review
- Track Q4 sole-source and amendment rates by department on a quarterly dashboard
- Consider multi-year budgeting for recurring needs to reduce the year-end rush

### Caveat

`reporting_period` records when a contract was *reported*, not when it was *awarded*. Some Q4 entries may be backlog from earlier quarters. This limitation is acknowledged but the pattern is too large and consistent to be explained by reporting lag alone.

---

## Insight 2: Contracts grow significantly through amendments

### The pattern

- **1 in 4 transaction rows is an amendment** (up from 1 in 6 pre-2019)
- Overall amendment rate: 20.9%. Post-2019: ~25%
- Of amended contracts: **24% more than double in value**, 2.6% grow by **500%+**

### By commodity type

| Commodity | Amendment rate (post-2019) |
|---|---|
| Services | 31.4% |
| Construction | 30.4% |
| Goods | 9.0% |

Services and construction are amended at 3x the rate of goods. This makes sense (more scope uncertainty) but also means these categories need proportionally more oversight.

### Extreme examples (excl. Defence)

| Vendor | Department | Original | Final | Growth |
|---|---|---|---|---|
| BGIS Global Integrated Solutions | PSPC | $768.5M | $1.89B | +146% |
| Bell Mobility | Shared Services Canada | $18.6M | $985.6M | +5,205% |
| Parsons Inc | PSPC | $49.8M | $991.4M | +1,890% |
| Vancouver Shipyards | Fisheries and Oceans | $179.9M | $849.9M | +372% |
| Ellisdon Corporation | PSPC | $0.2M | $623.4M | +263,069% |

### Connection to Q4

Amendments spike in Q4 (28.2% vs 23.3% in Q1-Q3). Year-end pressure drives both new awards and scope expansion on existing contracts.

### Recommendations

- Set amendment thresholds - if cumulative amendments exceed 50% of original value, require documented justification or re-compete
- Separate routine amendments (small extensions) from material ones (scope changes) by size relative to original value
- Track amendment rates by commodity type - services and construction need more oversight than goods
- Watch Q4 amendments specifically - year-end pressure drives both channels

### Caveat

We estimate growth by comparing `MAX(contract_value)` to `MIN(original_value)` across rows sharing a `procurement_id`. This depends on consistent reporting across amendment entries.

---

## How the insights connect

These aren't separate problems. They're two sides of the same coin.

Q4 pressure drives both new awards and amendments. Contracts awarded under year-end pressure get amended later, growing beyond their original scope. 24% of amended contracts more than double in value. Construction - the category most affected by the Q4 surge - also has the second-highest amendment rate.

Together, they paint a picture of procurement under budget-cycle pressure: rushed awards, expanded scope, and increasing concentration of spending in the final quarter.

### Federal benchmarks

| Metric | Federal benchmark |
|---|---|
| Q4 contract count vs Q1-Q3 average | +32% |
| Q4 average value multiplier (post-2022) | 1.89x |
| Q4 construction value multiplier | 5.84x |
| Amendment rate (post-2019) | ~25% |
| Amended contracts that more than double | 24% |
| Q4 amendment rate vs Q1-Q3 | 28.2% vs 23.3% |

These are numbers any government procurement office can compare against.

---

## Minor finding: vendor name inconsistency

The same vendor appears under different spellings throughout the dataset. Examples:

| Variant 1 | Variant 2 | Combined rows |
|---|---|---|
| CANADIAN CORPS OF COMMISSIONAIRES | Canadian Corps of Commissionaires | 5,700+ |
| STANTEC CONSULTING LTD. | Stantec Consulting Ltd. | 2,900+ |
| NISHA TECHNOLOGIES INC. | Nisha Technologies Inc. | 3,000+ |

This is a data engineering issue, not an analytical insight. But it means any vendor-level analysis (concentration, total awards) will undercount true concentration until names are normalized.

---

## What I'd investigate next

1. **Do Q4 contracts get amended more than Q1-Q3 contracts?** We showed amendments are more common *in* Q4, but are contracts *awarded* in Q4 more likely to be amended later? That would confirm the "rushed award, expanded later" hypothesis.

2. **Which specific contract descriptions drive the Q4 construction surge?** Is it road work, building maintenance, marine infrastructure? Knowing the category would sharpen the recommendation.

3. **How do amendment patterns differ by contract size?** Are small contracts amended at the same rate as large ones, or is growth concentrated in high-value contracts?

4. **Vendor-level amendment patterns** - after normalizing vendor names, do certain vendors receive disproportionately more amendments? That could indicate strategic low-bidding followed by scope expansion.

---

## Technical approach

| Phase | Notebook | Purpose |
|---|---|---|
| 1 | `phase1-exploration.ipynb` | Understand the dataset: size, grain, columns, missing data, time range |
| 2 | `phase2-profiling.ipynb` | Profile key fields, follow threads, decide which patterns to investigate |
| 3 | `phase3-analysis.ipynb` | Deep-dive into two insights with evidence, charts, and recommendations |

**Tools used**: DuckDB (SQL queries), Polars (DataFrames), Plotly (interactive charts), Python

**Key technical decisions**:
- Loaded all columns as VARCHAR to avoid type-guessing issues, cast manually with TRY_CAST
- Created a reusable SQL view excluding Defence and filtering to valid reporting periods
- Analyzed three eras separately where field availability differs
- Used `ROLLUP` for overall-vs-era comparisons in a single query
