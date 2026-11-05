# Junior Product Manager - Test Assignment

This project is a test assignment for the Junior Product Manager position at Disqover Agency.

The task was to analyze the plant pots market on Amazon.com using data on 50 popular search queries and 50 competing products. It included identifying customer preferences and search trends, comparing competitors by sales, calculating average price, sales, reviews and total revenue, and exploring possible reasons behind the best-selling product's performance.

## Project files

- `01-keyword-analysis/analyze_keywords.py` - analyzes search queries, product characteristics, search volumes and trends.
- `02-competitor-analysis/analyze_competitors.py` - analyzes competitor sales, prices, reviews and revenue.
- `03-cross-analysis/compare_market_data.py` - compares search demand with product sales and other product characteristics.
- `04-visualizations/create_charts.py` - creates charts to visualize the analysis results.

The `data` folders contain the original CSV files, `results` folders contain the analysis outputs, and `charts` contains the generated visualizations.

## How to run

Install the required libraries:

```bash
pip install matplotlib numpy
```

Run the scripts from the project root:

```bash
python 01-keyword-analysis/analyze_keywords.py
python 02-competitor-analysis/analyze_competitors.py
python 03-cross-analysis/compare_market_data.py
python 04-visualizations/create_charts.py
```

The scripts generate text reports and charts in their respective folders.