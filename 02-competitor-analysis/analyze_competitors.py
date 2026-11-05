
import csv
import textwrap
from collections import defaultdict
from pathlib import Path

folder = Path(__file__).resolve().parent
data_folder = folder / "data"
results_folder = folder / "results"

results_folder.mkdir(exist_ok=True)

input_file = data_folder / "Тестове 2026_Junior Product Manager_ - Список конкурентів.csv"
output_file = results_folder / "competitor_details.txt"
summary_file = results_folder / "competitor_summary.txt"


def get_number(value):
    value = str(value).replace(" ", "").replace("\u00a0", "")
    value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return None


def format_number(value, decimals=2):
    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}"


def make_table(headers, rows, group_index=None, wrap_column=None):
    if not rows:
        return "No data"

    widths = [
        max(
            len(str(headers[i])),
            max(len(str(row[i])) for row in rows)
        )
        for i in range(len(headers))
    ]

    if wrap_column is not None:
        widths[wrap_column] = 40

    def format_row(row):
        return " | ".join(
            str(row[i]).ljust(widths[i])
            for i in range(len(headers))
        )

    lines = [
        format_row(headers),
        "-+-".join("-" * width for width in widths)
    ]

    previous_group = None

    for row in rows:
        if group_index is not None:
            group = row[group_index]

            if previous_group is not None and group != previous_group:
                lines.append("")

            previous_group = group

        wrapped = []

        for i, value in enumerate(row):
            if i == wrap_column:
                parts = textwrap.wrap(
                    str(value),
                    width=widths[i],
                    break_long_words=False,
                    break_on_hyphens=False
                )
                wrapped.append(parts or [""])
            else:
                wrapped.append([str(value)])

        height = max(len(parts) for parts in wrapped)

        for line_number in range(height):
            line = []

            for i in range(len(headers)):
                value = (
                    wrapped[i][line_number]
                    if line_number < len(wrapped[i])
                    else ""
                )

                line.append(value.ljust(widths[i]))

            lines.append(" | ".join(line))

    return "\n".join(lines)


with open(input_file, encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)
    data = list(reader)


for item in data:
    item["Brand"] = item["Brand"].strip()
    item["Price"] = get_number(item["Price  USD"])
    item["Sales"] = get_number(item["ASIN Sales"])
    item["Revenue"] = get_number(item["ASIN Revenue"])
    item["Fees"] = get_number(item["Fees  USD"])
    item["Rating"] = get_number(item["Ratings"])
    item["Reviews"] = get_number(item["Review Count"])
    item["BSR Number"] = get_number(item["BSR"])


data.sort(
    key=lambda item: (
        item["Brand"].lower(),
        item["Price"] if item["Price"] is not None else float("inf")
    )
)


detail_headers = [
    "Brand",
    "Product",
    "Price",
    "Sales",
    "Revenue",
    "Fees",
    "Rating",
    "Reviews",
    "BSR"
]

detail_rows = []

for item in data:
    detail_rows.append([
        item["Brand"],
        item["Product Details"],
        format_number(item["Price"]),
        format_number(item["Sales"], 0),
        format_number(item["Revenue"]),
        format_number(item["Fees"]),
        format_number(item["Rating"], 1),
        format_number(item["Reviews"], 0),
        format_number(item["BSR Number"], 0)
    ])


detail_table = make_table(
    detail_headers,
    detail_rows,
    group_index=0,
    wrap_column=1
)


with open(output_file, "w", encoding="utf-8") as file:
    file.write(detail_table)


brands = defaultdict(list)

for item in data:
    brands[item["Brand"]].append(item)


brand_results = []

for brand, products in brands.items():
    total_sales = sum(
        item["Sales"] for item in products
        if item["Sales"] is not None
    )

    total_revenue = sum(
        item["Revenue"] for item in products
        if item["Revenue"] is not None
    )

    prices = [
        item["Price"] for item in products
        if item["Price"] is not None
    ]

    sales = [
        item["Sales"] for item in products
        if item["Sales"] is not None
    ]

    reviews = [
        item["Reviews"] for item in products
        if item["Reviews"] is not None
    ]

    average_price = sum(prices) / len(prices) if prices else None
    average_sales = sum(sales) / len(sales) if sales else None
    average_reviews = sum(reviews) / len(reviews) if reviews else None

    brand_results.append({
        "Brand": brand,
        "Products": len(products),
        "Total sales": total_sales,
        "Total revenue": total_revenue,
        "Average price": average_price,
        "Average sales": average_sales,
        "Average reviews": average_reviews
    })


brand_results.sort(
    key=lambda item: item["Total sales"],
    reverse=True
)


summary_headers = [
    "Brand",
    "Products",
    "Total sales",
    "Total revenue",
    "Average price",
    "Average sales",
    "Average reviews"
]

summary_rows = []

for item in brand_results:
    summary_rows.append([
        item["Brand"],
        item["Products"],
        format_number(item["Total sales"], 0),
        format_number(item["Total revenue"]),
        format_number(item["Average price"]),
        format_number(item["Average sales"]),
        format_number(item["Average reviews"])
    ])


brand_table = make_table(
    summary_headers,
    summary_rows
)


total_sales = sum(
    item["Sales"] for item in data
    if item["Sales"] is not None
)

total_revenue = sum(
    item["Revenue"] for item in data
    if item["Revenue"] is not None
)


def average_column(column):
    values = [
        item[column] for item in data
        if item[column] is not None
    ]

    return sum(values) / len(values) if values else None


average_price = average_column("Price")
average_sales = average_column("Sales")
average_reviews = average_column("Reviews")


market_headers = [
    "Metric",
    "Value"
]

market_rows = [
    ["Total products", len(data)],
    ["Total brands", len(brands)],
    ["Average price, USD", format_number(average_price)],
    ["Average sales", format_number(average_sales)],
    ["Average reviews", format_number(average_reviews)],
    ["Total sales", format_number(total_sales, 0)],
    ["Total revenue, USD", format_number(total_revenue)]
]

market_table = make_table(
    market_headers,
    market_rows
)


product_leader = max(
    data,
    key=lambda item: (
        item["Sales"]
        if item["Sales"] is not None
        else float("-inf")
    )
)

brand_leader = brand_results[0]


leader_headers = [
    "Metric",
    "Value"
]

leader_rows = [
    ["Brand", product_leader["Brand"]],
    ["Product", product_leader["Product Details"]],
    ["ASIN", product_leader["ASIN"]],
    ["Sales", format_number(product_leader["Sales"], 0)],
    ["Revenue, USD", format_number(product_leader["Revenue"])],
    ["Price, USD", format_number(product_leader["Price"])]
]

product_leader_table = make_table(
    leader_headers,
    leader_rows,
    wrap_column=1
)


brand_leader_rows = [
    ["Brand", brand_leader["Brand"]],
    ["Products", brand_leader["Products"]],
    ["Total sales", format_number(brand_leader["Total sales"], 0)],
    ["Total revenue, USD", format_number(brand_leader["Total revenue"])]
]

brand_leader_table = make_table(
    leader_headers,
    brand_leader_rows
)


summary = []

summary.append("1. Brands sorted by total sales")
summary.append("=" * 31)
summary.append(brand_table)
summary.append("")

summary.append("2. Market averages and totals")
summary.append("=" * 29)
summary.append(market_table)
summary.append("")

summary.append("3. Best-selling product")
summary.append("=" * 23)
summary.append(product_leader_table)
summary.append("")

summary.append("4. Best-selling brand")
summary.append("=" * 21)
summary.append(brand_leader_table)
summary.append("")


summary_text = "\n".join(summary)

with open(summary_file, "w", encoding="utf-8") as file:
    file.write(summary_text)


print()
print(detail_table)

print()
print("Total products:", len(data))
print("Total brands:", len(brands))

print()
print("Detailed table:", output_file)
print("Summary:", summary_file)
