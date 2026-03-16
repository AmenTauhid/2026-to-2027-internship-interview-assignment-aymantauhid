# Government of Canada Contracts - Data Analysis

Analysis of the Government of Canada's "Contracts over $10,000" dataset (1.26M rows, 43 columns) to find actionable procurement insights.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env and set LOCAL_DATASET_PATH to your contracts.csv location
cp .env.example .env

# Download the dataset from:
# https://open.canada.ca/data/en/dataset/d8f85d91-7dec-4fd1-8055-483b77225d8b
# Save to data/contracts.csv
```

## Notebooks

Run in order:

| Notebook | Purpose |
|---|---|
| `notebooks/phase1-exploration.ipynb` | Understand the dataset: size, grain, columns, missing data |
| `notebooks/phase2-profiling.ipynb` | Profile key fields, identify patterns worth investigating |
| `notebooks/phase3-analysis.ipynb` | Deep-dive into two insights with evidence and recommendations |

## Deliverables

| File | Format |
|---|---|
| `deliverables/FINDINGS-REPORT.md` | Written report summarizing all findings |
| `deliverables/app.py` | Interactive Streamlit dashboard |

To run the dashboard:
```bash
streamlit run deliverables/app.py
```

## Key Findings

1. **Q4 fiscal year-end spending surge** - 32% more contracts than Q1-Q3 average, construction values 5.84x higher in Q4, amendments also concentrated in Q4
2. **Contract amendment growth** - 1 in 4 rows is an amendment (up from 1 in 6 pre-2019), 24% of amended contracts more than double in value

## Tools Used

DuckDB, Polars, Plotly, Matplotlib, Streamlit, Python
