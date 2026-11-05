
import csv
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

root = Path(__file__).resolve().parent.parent
output = Path(__file__).resolve().parent / "charts"
output.mkdir(parents=True, exist_ok=True)

keyword_file = root / "01-keyword-analysis" / "results" / "keyword_details.txt"
product_file = root / "02-competitor-analysis" / "data" / "Тестове 2026_Junior Product Manager_ - Список конкурентів.csv"

navy = "#263548"
slate = "#677584"
blue = "#6487A0"
teal = "#598E86"
sand = "#C49B6C"
rose = "#B77A7A"
purple = "#877F9F"
sage = "#87967C"
grid_color = "#E7EAED"
background = "#FFFFFF"

colors = {
    "Size": blue,
    "Material": teal,
    "Purpose": purple,
    "Functionality": sand,
    "Design": rose,
    "Plant Type": sage,
    "General": slate,
    "Combined Features": "#77979D"
}

category_order = list(colors)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "figure.facecolor": background,
    "axes.facecolor": background,
    "savefig.facecolor": background,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.edgecolor": grid_color,
    "text.color": navy,
    "axes.labelcolor": slate,
    "xtick.color": slate,
    "ytick.color": navy,
    "axes.titleweight": "bold",
    "axes.titlesize": 15
})


def number(value):
    text = str(value or "").strip()
    text = text.replace("\u00a0", "")
    text = text.replace(" ", "")
    text = text.replace("$", "")
    text = text.replace("%", "")
    text = text.replace(",", ".")

    try:
        result = float(text)
        return result if math.isfinite(result) else None
    except ValueError:
        return None


def integer(value):
    text = str(value or "").strip()
    text = text.replace("\u00a0", "")
    text = text.replace(" ", "")
    text = text.replace(",", "")
    text = text.replace(">", "")

    try:
        return int(text)
    except ValueError:
        return None

def mean(values):
    valid = [
        value for value in values
        if value is not None
    ]

    return sum(valid) / len(valid) if valid else None


def average(values):
    valid = [
        value for value in values
        if value is not None
    ]

    return sum(valid) / len(valid) if valid else None


def save(fig, filename):
    fig.savefig(
        output / filename,
        dpi=200,
        bbox_inches="tight",
        pad_inches=0.3
    )

    plt.close(fig)


def apply_style(ax, xlabel, ylabel):
    ax.set_xlabel(
        xlabel,
        fontsize=10,
        labelpad=10
    )

    ax.set_ylabel(
        ylabel,
        fontsize=10,
        labelpad=12
    )

    ax.grid(
        axis="x",
        color=grid_color,
        linewidth=0.7
    )

    ax.set_axisbelow(True)
    ax.tick_params(length=0, pad=6)

    ax.xaxis.set_major_formatter(
        FuncFormatter(
            lambda value, _: f"{value:,.0f}"
        )
    )


def set_title(ax, title):
    ax.set_title(
        title,
        loc="center",
        fontsize=15,
        fontweight="bold",
        pad=22
    )


def read_keywords():
    lines = keyword_file.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    result = []

    for line in lines[2:]:
        parts = [
            part.strip()
            for part in line.split("|")
        ]

        if len(parts) != 7:
            continue

        category, feature, keywords, searches, trend, competition, level = parts

        if category not in category_order:
            continue

        result.append({
            "category": category,
            "feature": feature,
            "keywords": integer(keywords),
            "searches": integer(searches),
            "trend": number(trend),
            "competition": competition,
            "level": level
        })

    if not result:
        raise ValueError(
            "No keyword data found in keyword_details.txt"
        )

    result.sort(
        key=lambda item: (
            category_order.index(item["category"]),
            -item["searches"]
        )
    )

    return result


def read_products():
    with product_file.open(
        encoding="utf-8-sig",
        newline=""
    ) as file:
        products = list(csv.DictReader(file))

    fields = {
        "sales": "ASIN Sales",
        "price": "Price  USD",
        "revenue": "ASIN Revenue",
        "reviews": "Review Count",
        "rating": "Ratings",
        "velocity": "Review velocity",
        "images": "Images"
    }

    for product in products:
        product["brand"] = (
            product["Brand"].strip() or "Unknown"
        )

        for key, column in fields.items():
            product[key] = number(
                product.get(column)
            )

        sponsored = str(
            product.get("Sponsored", "")
        ).strip().lower()

        product["sponsored"] = (
            "Sponsored"
            if sponsored not in {
                "", "no", "false", "0", "n/a", "-"
            }
            else "Not sponsored"
        )

        badge = str(
            product.get("Best Seller", "")
        ).strip().lower()

        product["badge"] = (
            "Best Seller"
            if badge in {"yes", "true", "1"}
            else "No badge"
        )

        try:
            created = datetime.strptime(
                product["Creation Date"].strip(),
                "%b %d, %Y"
            )

            product["age"] = max(
                0,
                (datetime(2026, 11, 5) - created).days / 30.44
            )

        except ValueError:
            product["age"] = None

    return products


def feature_match(title, feature):
    title = title.lower()

    aliases = {
        "ceramic": r"\b(?:ceramic|porcelain|stoneware)\b",
        "terracotta": r"\b(?:terracotta|terra cotta)\b",
        "clear": r"\b(?:clear|transparent)\b",
        "drainage": r"\b(?:drainage|draining|drain)\b",
        "saucers": r"\b(?:saucer|saucers|trays?|pallet)\b",
        "snake": r"\bsnake\s+plants?\b",
        "spider": r"\bspider\s+plants?\b",
        "house": r"\bhouse\s?plants?\b",
        "outdoor": r"\bout\s?door\b",
        "stand": r"\bstands?\b"
    }

    if feature.endswith(" inch"):
        size = feature.split()[0]

        single = (
            rf'(?<!\d){size}(?:\.0)?\s*'
            rf'(?:inches|inch|in\b|["”])'
        )

        if re.search(single, title):
            return True

        grouped_pattern = (
            r'(\d+(?:\.\d+)?(?:\s*[/,+]\s*'
            r'\d+(?:\.\d+)?)+)\s*'
            r'(?:inches|inch|in\b|["”])'
        )

        for chunk in re.finditer(
            grouped_pattern,
            title
        ):
            values = re.findall(
                r"\d+(?:\.\d+)?",
                chunk.group(1)
            )

            if any(
                float(value) == float(size)
                for value in values
            ):
                return True

        return False

    pattern = aliases.get(
        feature,
        rf"\b{re.escape(feature)}\b"
    )

    return bool(re.search(pattern, title))


def matches(product, characteristic):
    if characteristic["category"] == "General":
        return True

    features = characteristic["feature"].split(" + ")

    return all(
        feature_match(
            product["Product Details"],
            feature
        )
        for feature in features
    )


def horizontal_chart(
    labels,
    values,
    title,
    xlabel,
    ylabel,
    filename,
    bar_colors=None,
    counts=None,
    value_format="integer",
    height=None,
    fontsize=9
):
    if not labels:
        return

    height = height or max(
        5.5,
        len(labels) * 0.44 + 2
    )

    fig, ax = plt.subplots(
        figsize=(13, height)
    )

    positions = np.arange(len(labels))

    if bar_colors is None:
        bar_colors = [teal] * len(labels)

    ax.barh(
        positions,
        values,
        color=bar_colors,
        height=0.65
    )

    ax.set_yticks(
        positions,
        labels,
        fontsize=fontsize
    )

    ax.invert_yaxis()

    maximum = max(values) if values else 1

    ax.set_xlim(
        0,
        maximum * 1.32 if maximum else 1
    )

    for index, value in enumerate(values):
        if value_format == "decimal":
            label = f"{value:,.1f}"
        elif value_format == "money":
            label = f"${value:,.0f}"
        else:
            label = f"{value:,.0f}"

        if counts is not None:
            total = counts[index]

            suffix = (
                "product" if total == 1
                else "products"
            )

            label += f"  |  {total} {suffix}"

        ax.text(
            value + maximum * 0.018,
            index,
            label,
            va="center",
            fontsize=8.5,
            color=navy
        )

    set_title(ax, title)
    apply_style(ax, xlabel, ylabel)

    fig.tight_layout()
    save(fig, filename)


def build_groups(products, selector, order=None):
    grouped = defaultdict(list)

    for product in products:
        value = selector(product)

        if (
            value is not None
            and product["sales"] is not None
        ):
            grouped[str(value)].append(product)

    if order is None:
        names = list(grouped)
    else:
        names = [
            value for value in order
            if value in grouped
        ]

    result = []

    for name in names:
        items = grouped[name]

        result.append({
            "name": name,
            "products": len(items),
            "total_sales": sum(
                product["sales"]
                for product in items
            ),
            "average_sales": average(
                product["sales"]
                for product in items
            )
        })

    return result


def group_chart(ax, groups, title, color):
    labels = [
        group["name"]
        for group in groups
    ]

    values = [
        group["average_sales"]
        for group in groups
    ]

    positions = np.arange(len(groups))

    ax.barh(
        positions,
        values,
        color=color,
        height=0.62
    )

    ax.set_yticks(
        positions,
        labels,
        fontsize=9
    )

    ax.invert_yaxis()

    maximum = max(values) if values else 1

    ax.set_xlim(
        0,
        maximum * 1.42 if maximum else 1
    )

    for index, group in enumerate(groups):
        count = group["products"]

        label = (
            f'{group["average_sales"]:,.1f}'
            f'  |  {count} '
            f'{"product" if count == 1 else "products"}'
        )

        ax.text(
            group["average_sales"] + maximum * 0.02,
            index,
            label,
            va="center",
            fontsize=9
        )

    set_title(ax, title)

    apply_style(
        ax,
        "Average units sold per product in 30 days",
        "Product group"
    )


def range_label(value, limits, labels):
    if value is None:
        return None

    for limit, label in zip(limits, labels):
        if value < limit:
            return label

    return labels[-1]


groups = read_keywords()
products = read_products()

leader = max(
    products,
    key=lambda product: product["sales"] or 0
)

for characteristic in groups:
    related = [
        product
        for product in products
        if matches(product, characteristic)
    ]

    characteristic["products"] = len(related)

    characteristic["sales"] = sum(
        product["sales"] or 0
        for product in related
    )


for old in output.glob("*.png"):
    old.unlink()


labels = [
    f'{item["category"]} / {item["feature"]}'
    for item in groups
]

horizontal_chart(
    labels,
    [item["searches"] for item in groups],
    "Search volume by product characteristic",
    "Number of searches",
    "Product characteristic",
    "01_search_preferences.png",
    bar_colors=[
        colors[item["category"]]
        for item in groups
    ],
    fontsize=8.5
)


trend_groups = [
    item for item in groups
    if item["trend"] is not None
]

trend_values = [
    item["trend"]
    for item in trend_groups
]

fig, ax = plt.subplots(
    figsize=(
        13,
        max(9, len(trend_groups) * 0.43 + 2)
    )
)

positions = np.arange(len(trend_groups))

ax.barh(
    positions,
    trend_values,
    color=[
        teal if value >= 0 else rose
        for value in trend_values
    ],
    height=0.65
)

ax.set_yticks(
    positions,
    [
        f'{item["category"]} / {item["feature"]}'
        for item in trend_groups
    ],
    fontsize=8.5
)

ax.invert_yaxis()
ax.axvline(0, color=slate, linewidth=1)

ax.set_xlim(
    min(trend_values + [0]) - 65,
    max(trend_values + [0]) + 80
)

for index, value in enumerate(trend_values):
    ax.text(
        value + (6 if value >= 0 else -6),
        index,
        f"{value:+g}%",
        va="center",
        ha="left" if value >= 0 else "right",
        fontsize=8.5
    )

set_title(
    ax,
    "Search volume changes by product characteristic"
)

ax.set_xlabel(
    "Search volume change, %",
    labelpad=10
)

ax.set_ylabel(
    "Product characteristic",
    labelpad=12
)

ax.grid(axis="x", color=grid_color)
ax.set_axisbelow(True)
ax.tick_params(length=0)

fig.tight_layout()
save(fig, "02_search_trends.png")


ranked = sorted(
    products,
    key=lambda product: product["sales"] or 0,
    reverse=True
)

horizontal_chart(
    [
        f'{index + 1:02d}  {product["brand"]} | {product["ASIN"]}'
        for index, product in enumerate(ranked)
    ],
    [
        product["sales"] or 0
        for product in ranked
    ],
    "Sales ranking of all 50 Amazon products",
    "Units sold in the last 30 days",
    "Product and ASIN",
    "03_competitor_sales_ranking.png",
    bar_colors=[
        sand if index == 0 else blue
        for index in range(len(ranked))
    ],
    height=20,
    fontsize=8
)


market_metrics = [
    (
        "Average product price",
        mean(product["price"] for product in products),
        "${:,.2f}"
    ),
    (
        "Average monthly sales",
        mean(product["sales"] for product in products),
        "{:,.2f} units"
    ),
    (
        "Average customer reviews",
        mean(product["reviews"] for product in products),
        "{:,.2f}"
    ),
    (
        "Combined revenue",
        sum(product["revenue"] or 0 for product in products),
        "${:,.2f}"
    )
]

fig, axes = plt.subplots(
    2,
    2,
    figsize=(12, 7)
)

for ax, (name, value, pattern), color in zip(
    axes.ravel(),
    market_metrics,
    [blue, teal, purple, sand]
):
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(
        0.5,
        0.65,
        name,
        ha="center",
        fontsize=13,
        color=slate
    )

    ax.text(
        0.5,
        0.38,
        pattern.format(value),
        ha="center",
        fontsize=24,
        fontweight="bold",
        color=color
    )

fig.suptitle(
    "Amazon plant pots market metrics",
    fontsize=17,
    fontweight="bold",
    x=0.5,
    ha="center"
)

fig.tight_layout()
save(fig, "04_market_metrics.png")


fig, axes = plt.subplots(
    1,
    2,
    figsize=(
        18,
        max(9, len(groups) * 0.43 + 2)
    ),
    sharey=True
)

positions = np.arange(len(groups))

for ax, key, color, xlabel in [
    (
        axes[0],
        "searches",
        blue,
        "Number of searches"
    ),
    (
        axes[1],
        "sales",
        sand,
        "Units sold by matching products"
    )
]:
    values = [
        item[key]
        for item in groups
    ]

    ax.barh(
        positions,
        values,
        color=color,
        height=0.65
    )

    maximum = max(values)

    ax.set_xlim(
        0,
        maximum * 1.3 if maximum else 1
    )

    for index, value in enumerate(values):
        ax.text(
            value + maximum * 0.017,
            index,
            f"{value:,.0f}",
            va="center",
            fontsize=8
        )

    ax.grid(
        axis="x",
        color=grid_color
    )

    ax.set_axisbelow(True)
    ax.set_xlabel(xlabel, labelpad=10)
    ax.tick_params(length=0)

    ax.xaxis.set_major_formatter(
        FuncFormatter(
            lambda value, _: f"{value:,.0f}"
        )
    )

axes[0].set_yticks(
    positions,
    labels,
    fontsize=8.5
)

axes[0].invert_yaxis()

axes[0].set_ylabel(
    "Product characteristic",
    labelpad=12
)

axes[1].tick_params(
    axis="y",
    labelleft=False
)

fig.suptitle(
    "Search demand compared with product sales",
    fontsize=16,
    fontweight="bold",
    x=0.5,
    ha="center"
)

fig.subplots_adjust(
    left=0.27,
    right=0.96,
    top=0.95,
    bottom=0.055,
    wspace=0.09
)

save(fig, "05_searches_vs_product_sales.png")


price_groups = defaultdict(list)

for product in products:
    if (
        product["price"] is not None
        and product["sales"] is not None
    ):
        price_groups[
            round(product["price"], 2)
        ].append(product)

price_rows = []

for price, items in price_groups.items():
    price_rows.append({
        "price": price,
        "products": len(items),
        "average_sales": average(
            product["sales"]
            for product in items
        ),
        "total_sales": sum(
            product["sales"]
            for product in items
        )
    })

price_rows.sort(
    key=lambda row: -row["average_sales"]
)

horizontal_chart(
    [
        f'${row["price"]:.2f}'
        for row in price_rows
    ],
    [
        row["average_sales"]
        for row in price_rows
    ],
    "Average product sales by exact price",
    "Average units sold per product in 30 days",
    "Product price, USD",
    "06_price_vs_sales.png",
    bar_colors=[
        sand
        if row["price"] == leader["price"]
        else teal
        for row in price_rows
    ],
    counts=[
        row["products"]
        for row in price_rows
    ],
    value_format="decimal"
)


ratings = sorted(
    {
        product["rating"]
        for product in products
        if product["rating"] is not None
    },
    reverse=True
)

rating_groups = build_groups(
    products,
    lambda product: (
        f'{product["rating"]:.1f} stars'
        if product["rating"] is not None
        else None
    ),
    [
        f"{rating:.1f} stars"
        for rating in ratings
    ]
)

review_labels = [
    "Under 100 reviews",
    "100 to 499 reviews",
    "500 to 999 reviews",
    "1,000 to 4,999 reviews",
    "5,000 or more reviews"
]

review_groups = build_groups(
    products,
    lambda product: range_label(
        product["reviews"],
        [100, 500, 1000, 5000, float("inf")],
        review_labels
    ),
    review_labels
)

velocity_labels = [
    "Under 10",
    "10 to 49",
    "50 to 99",
    "100 or more"
]

velocity_groups = build_groups(
    products,
    lambda product: range_label(
        product["velocity"],
        [10, 50, 100, float("inf")],
        velocity_labels
    ),
    velocity_labels
)

fig, axes = plt.subplots(
    3,
    1,
    figsize=(14, 17)
)

group_chart(
    axes[0],
    rating_groups,
    "Customer rating",
    blue
)

group_chart(
    axes[1],
    review_groups,
    "Number of customer reviews",
    teal
)

group_chart(
    axes[2],
    velocity_groups,
    "Review velocity",
    purple
)

fig.suptitle(
    "Customer feedback and average product sales",
    fontsize=17,
    fontweight="bold",
    x=0.5,
    ha="center"
)

fig.tight_layout(
    rect=[0, 0, 1, 0.96],
    h_pad=3
)

save(fig, "07_customer_feedback_vs_sales.png")


sponsored_groups = build_groups(
    products,
    lambda product: product["sponsored"],
    ["Sponsored", "Not sponsored"]
)

badge_groups = build_groups(
    products,
    lambda product: product["badge"],
    ["Best Seller", "No badge"]
)

age_labels = [
    "Under 6 months",
    "6 to 11 months",
    "12 to 35 months",
    "36 months or more"
]

age_groups = build_groups(
    products,
    lambda product: range_label(
        product["age"],
        [6, 12, 36, float("inf")],
        age_labels
    ),
    age_labels
)

fig, axes = plt.subplots(
    3,
    1,
    figsize=(14, 16)
)

group_chart(
    axes[0],
    sponsored_groups,
    "Sponsored advertising",
    sand
)

group_chart(
    axes[1],
    badge_groups,
    "Best Seller badge",
    purple
)

group_chart(
    axes[2],
    age_groups,
    "Product listing age",
    teal
)

fig.suptitle(
    "Advertising and listing performance",
    fontsize=17,
    fontweight="bold",
    x=0.5,
    ha="center"
)

fig.tight_layout(
    rect=[0, 0, 1, 0.96],
    h_pad=3
)

save(fig, "08_advertising_and_listing_vs_sales.png")


other_products = [
    product
    for product in products
    if product["ASIN"] != leader["ASIN"]
]

leader_features = [
    item["feature"]
    for item in groups
    if item["category"] not in {
        "General",
        "Combined Features"
    }
    and matches(leader, item)
]

other_velocity = mean(
    product["velocity"]
    for product in other_products
)

other_age = mean(
    product["age"]
    for product in other_products
)

leader_rows = [
    [
        "Product price",
        f'${leader["price"]:,.2f}',
        f'${mean(p["price"] for p in other_products):,.2f}'
    ],
    [
        "Monthly units sold",
        f'{leader["sales"]:,.0f}',
        f'{mean(p["sales"] for p in other_products):,.1f}'
    ],
    [
        "Customer rating",
        f'{leader["rating"]:.1f}',
        f'{mean(p["rating"] for p in other_products):.2f}'
    ],
    [
        "Customer reviews",
        f'{leader["reviews"]:,.0f}',
        f'{mean(p["reviews"] for p in other_products):,.1f}'
    ],
    [
        "Review velocity",
        f'{leader["velocity"]:.0f}'
        if leader["velocity"] is not None
        else "N/A",
        f"{other_velocity:,.1f}"
        if other_velocity is not None
        else "N/A"
    ],
    [
        "Sponsored advertising",
        leader["sponsored"],
        f'{sum(p["sponsored"] == "Sponsored" for p in other_products)} of 49'
    ],
    [
        "Best Seller badge",
        leader["badge"],
        f'{sum(p["badge"] == "Best Seller" for p in other_products)} of 49'
    ],
    [
        "Listing age",
        f'{leader["age"]:.1f} months'
        if leader["age"] is not None
        else "N/A",
        f"{other_age:.1f} months"
        if other_age is not None
        else "N/A"
    ],
    [
        "Product characteristics",
        ", ".join(leader_features),
        "See characteristic analysis"
    ]
]

fig, ax = plt.subplots(
    figsize=(15, 6)
)

ax.axis("off")

ax.set_title(
    f'Top-selling product: {leader["brand"]} | {leader["ASIN"]}',
    fontsize=16,
    fontweight="bold",
    loc="center",
    pad=20
)

comparison_table = ax.table(
    cellText=leader_rows,
    colLabels=[
        "Factor",
        "Top-selling product",
        "Other 49 products"
    ],
    cellLoc="left",
    colLoc="left",
    loc="center",
    colWidths=[0.27, 0.39, 0.34]
)

comparison_table.auto_set_font_size(False)
comparison_table.set_fontsize(9)
comparison_table.scale(1, 1.8)

for (row, column), cell in comparison_table.get_celld().items():
    cell.set_edgecolor(grid_color)

    if row == 0:
        cell.set_facecolor("#EEF2F4")
        cell.get_text().set_weight("bold")
    elif row % 2 == 0:
        cell.set_facecolor("#F7F9FA")
    else:
        cell.set_facecolor("white")

fig.tight_layout()
save(fig, "09_sales_leader_comparison.png")
