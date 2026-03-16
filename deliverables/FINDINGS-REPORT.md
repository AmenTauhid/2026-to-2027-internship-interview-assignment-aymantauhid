# Government of Canada Contracts Over $10,000 - Findings Report

## What is this dataset?

1.26 million rows of federal contract data spanning fiscal years 2004-2025, covering 99 government departments and 208,000+ vendors. Each row is a **transaction** - a new contract, an amendment, or a standing offer - not a unique contract. The `procurement_id` field links a contract to its amendments.

**Scope decisions for this analysis:**
- National Defence excluded (structurally different procurement - shipbuilding, fighter jets - skews all civilian patterns)
- Only rows with valid `reporting_period` format (filters out ~2,600 malformed entries)
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

1. **Malformed reporting_period**: ~2,600 rows with values like "C", "Q1", "2010-11-Q4", "2108-2019". Excluded from time-based analysis.
2. **Vendor name inconsistency**: Same vendor under multiple spellings (case, periods, abbreviations). "Canadian Corps of Commissionaires" appears under 10+ variants with 10,000+ rows combined. Vendor-level counts may undercount true concentration.
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

Canada's fiscal year ends March 31. Q4 (January-March) consistently shows a volume surge:
- **38% more contracts** than the Q1-Q3 average
- But Q4's share of total value is ~25% - roughly proportional
- Q4 average contract value is actually **lower** ($657K vs $903K for Q1-Q3)
- The pattern is a rush of many smaller contracts, not fewer large ones

### What's being rushed

The volume surge is consistent across commodity types, but average values in Q4 are actually lower across the board. This suggests departments are clearing backlogs of smaller procurements at fiscal year-end rather than pushing through large contracts.

### How it happens

The year-end rush operates through two channels:
- **New contracts**: 30.6% of all new contracts are in Q4
- **Amendments**: 34.7% of all amendments are in Q4 - even more concentrated than new awards

The non-competitive (sole-source) rate is also slightly higher in Q4: 33.9% vs 32.9% in Q1-Q3.

### Era comparison

| Era | Q4 value multiplier | Notes |
|---|---|---|
| Pre-2019 | 1.24x | Mild Q4 value premium (but `reporting_period` was not mandatory) |
| 2019-2022 | 1.06x | Slight Q4 premium |
| Post-2022 | 0.87x | Q4 value actually *lower* than other quarters |

The volume surge is consistent across all eras, but the value pattern has shifted. In recent years, Q4 sees many more contracts at lower average values - consistent with a "use it or lose it" pattern of clearing smaller procurements before fiscal year-end.

### Recommendations

- Flag the high volume of Q4 contracts for quality review - rushed smaller contracts may still carry risk
- Track Q4 sole-source and amendment rates by department on a quarterly dashboard
- Consider multi-year budgeting for recurring needs to reduce the year-end rush

### Caveat

`reporting_period` records when a contract was *reported*, not when it was *awarded*. Some Q4 entries may be backlog from earlier quarters. This limitation is acknowledged but the pattern is too large and consistent to be explained by reporting lag alone.

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

| Metric | Federal benchmark |
|---|---|
| Q4 contract count vs Q1-Q3 average | +38% |
| Q4 construction value (post-2019) | 63% lands in Q4 (5.8x avg multiplier) |
| Amendment rate (post-2019) | ~25% |
| Amended contracts that more than double | 40% |
| Services amendment rate (post-2022) | 31.8% |
| Top 50 vendor share of total spend | 55% |
| Top 50 vendor amendment rate | 37.7% (vs 20.5% for others) |
| Departments with >30% single-vendor dependency | 18 out of 97 |
| Q4 amendment rate vs Q1-Q3 | 25.7% vs 22.2% |

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

**Tools used**: DuckDB (SQL queries), Polars (DataFrames), Plotly (interactive charts), Python

**Key technical decisions**:
- Loaded all columns as VARCHAR to avoid type-guessing issues, cast manually with TRY_CAST
- Created a reusable SQL view excluding Defence and filtering to valid reporting periods
- Analyzed three eras separately where field availability differs
- Used `ROLLUP` for overall-vs-era comparisons in a single query
