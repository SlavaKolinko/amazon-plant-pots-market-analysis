
import csv
import re
from collections import defaultdict
from pathlib import Path

folder = Path(__file__).resolve().parent
data_folder = folder / "data"
results_folder = folder / "results"

results_folder.mkdir(exist_ok=True)

input_file = data_folder / "Тестове 2026_Junior Product Manager_ - Список пошукових слів.csv"
output_file = results_folder / "keyword_details.txt"
summary_file = results_folder / "keyword_summary.txt"

categories = {
    "Size": ["small", "large", "big", "mini", "4 inch", "5 inch", "6 inch", "7 inch", "8 inch", "10 inch"],
    "Material": ["ceramic", "plastic", "terracotta"],
    "Purpose": ["indoor", "outdoor", "house"],
    "Functionality": ["drainage", "stand", "saucers", "smart"],
    "Design": ["clear", "white", "black", "pink", "funny", "cute", "unique", "decorative", "boho", "tamagotchi", "peeing", "gepege"],
    "Plant Type": ["snake", "spider"]
}

stop_words = {
    "plant", "pot", "pots", "with",
    "for", "and", "the", "of", "a"
}

feature_categories = {
    feature: category
    for category, features in categories.items()
    for feature in features
}


def get_features(phrase):
    phrase = phrase.lower()

    sizes = re.findall(r"\b\d+\s*(?:inch|inches)\b", phrase)
    phrase = re.sub(r"\b\d+\s*(?:inch|inches)\b", " ", phrase)

    words = re.findall(r"[a-z]+", phrase)
    features = [word for word in words if word not in stop_words]

    for size in sizes:
        number = re.search(r"\d+", size).group()
        features.append(number + " inch")

    return sorted(set(features))


def get_number(value):
    return int(value.replace(",", "").replace(">", "").strip())


def get_trend(value):
    value = value.replace("%", "").strip()

    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def get_competition_level(value):
    if value < 5000:
        return "Low"
    if value < 20000:
        return "Medium"
    return "High"


def format_trend(value):
    if value is None:
        return "N/A"
    return f"{value:+g}%"


def make_table(headers, rows, category_index=None):
    if not rows:
        return "No data"

    widths = [
        max(
            len(str(headers[i])),
            max(len(str(row[i])) for row in rows)
        )
        for i in range(len(headers))
    ]

    def format_row(row):
        return " | ".join(
            str(row[i]).ljust(widths[i])
            for i in range(len(headers))
        )

    lines = [
        format_row(headers),
        "-+-".join("-" * width for width in widths)
    ]

    previous_category = None

    for row in rows:
        if category_index is not None:
            category = row[category_index]

            if previous_category is not None and category != previous_category:
                lines.append("")

            previous_category = category

        lines.append(format_row(row))

    return "\n".join(lines)


data = defaultdict(list)

with open(input_file, encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        features = get_features(row["Keyword Phrase"])

        if not features:
            category = "General"
            characteristic = "plant pot"

        elif len(features) == 1:
            characteristic = features[0]
            category = feature_categories.get(characteristic, "Other")

        else:
            category = "Combined Features"
            characteristic = " + ".join(features)

        data[(category, characteristic)].append(row)


results = []

for (category, characteristic), rows in data.items():
    total_volume = 0
    total_trend = 0
    total_competition = 0
    missing_trend = False
    approximate = False

    for row in rows:
        volume = get_number(row["Search Volume, q./last month"])
        trend = get_trend(row["Search Volume Trend, %"])
        competition_text = row["Competing Products"]

        total_volume += volume
        total_competition += get_number(competition_text)

        if trend is None:
            missing_trend = True
        else:
            total_trend += trend

        if ">" in competition_text:
            approximate = True

    competition_result = (
        f">{total_competition:,}"
        if approximate
        else f"{total_competition:,}"
    )

    results.append({
        "Category": category,
        "Characteristic": characteristic,
        "Keywords": len(rows),
        "Search Volume": total_volume,
        "Trend": None if missing_trend else total_trend,
        "Competing Products": competition_result,
        "Competition Number": total_competition,
        "Competition Approximate": approximate,
        "Competition Level": get_competition_level(total_competition)
    })


category_order = list(categories) + [
    "General", "Other", "Combined Features"
]

results.sort(
    key=lambda item: (
        category_order.index(item["Category"]),
        -item["Search Volume"]
    )
)


detail_headers = [
    "Category",
    "Characteristic",
    "Keywords",
    "Search volume",
    "Trend, %",
    "Competing products",
    "Competition level"
]

detail_rows = [
    [
        item["Category"],
        item["Characteristic"],
        item["Keywords"],
        f'{item["Search Volume"]:,}',
        format_trend(item["Trend"]),
        item["Competing Products"],
        item["Competition Level"]
    ]
    for item in results
]

detail_table = make_table(
    detail_headers,
    detail_rows,
    category_index=0
)

with open(output_file, "w", encoding="utf-8") as file:
    file.write(detail_table)


category_results = []

for category in categories:
    items = [
        item for item in results
        if item["Category"] == category
    ]

    if not items:
        continue

    trends = [item["Trend"] for item in items]

    category_results.append({
        "Category": category,
        "Search Volume": sum(item["Search Volume"] for item in items),
        "Trend": sum(trends) if all(t is not None for t in trends) else None,
        "Competition": sum(item["Competition Number"] for item in items),
        "Competition Approximate": any(item["Competition Approximate"] for item in items),
        "Items": items
    })


summary = []


def add_section(title, headers, rows):
    summary.append(title)
    summary.append("=" * len(title))
    summary.append(make_table(headers, rows))
    summary.append("")
    summary.append("")


def trend_rows(items, reverse=True):
    valid = [
        item for item in items
        if item["Trend"] is not None
    ]

    return [
        [
            item["Category"],
            item["Characteristic"],
            format_trend(item["Trend"]),
            f'{item["Search Volume"]:,}'
        ]
        for item in sorted(
            valid,
            key=lambda x: x["Trend"],
            reverse=reverse
        )
    ]


add_section(
    "1. Categories with the highest search volume",
    ["Category", "Search volume"],
    [
        [item["Category"], f'{item["Search Volume"]:,}']
        for item in sorted(
            category_results,
            key=lambda x: -x["Search Volume"]
        )
    ]
)


best_volume = []
worst_volume = []

for category in category_results:
    best = max(category["Items"], key=lambda x: x["Search Volume"])
    worst = min(category["Items"], key=lambda x: x["Search Volume"])

    best_volume.append([
        category["Category"],
        best["Characteristic"],
        f'{best["Search Volume"]:,}'
    ])

    worst_volume.append([
        category["Category"],
        worst["Characteristic"],
        f'{worst["Search Volume"]:,}'
    ])


add_section(
    "2. Most popular characteristic in each category",
    ["Category", "Characteristic", "Search volume"],
    best_volume
)

add_section(
    "3. Least popular characteristic in each category",
    ["Category", "Characteristic", "Search volume"],
    worst_volume
)


growing = [
    item for item in results
    if item["Trend"] is not None and item["Trend"] > 0
]

declining = [
    item for item in results
    if item["Trend"] is not None and item["Trend"] < 0
]


add_section(
    "4. Characteristics with the highest trend growth",
    ["Category", "Characteristic", "Trend, %", "Search volume"],
    trend_rows(growing)
)

add_section(
    "5. Characteristics with the largest trend decline",
    ["Category", "Characteristic", "Trend, %", "Search volume"],
    trend_rows(declining, reverse=False)
)


valid_categories = [
    item for item in category_results
    if item["Trend"] is not None
]


add_section(
    "6. Categories with the highest sum of trends",
    ["Category", "Sum of trends"],
    [
        [item["Category"], format_trend(item["Trend"])]
        for item in sorted(
            valid_categories,
            key=lambda x: -x["Trend"]
        )
    ]
)

add_section(
    "7. Categories with the lowest sum of trends",
    ["Category", "Sum of trends"],
    [
        [item["Category"], format_trend(item["Trend"])]
        for item in sorted(
            valid_categories,
            key=lambda x: x["Trend"]
        )
    ]
)


best_trends = []
worst_trends = []

for category in category_results:
    items = [
        item for item in category["Items"]
        if item["Trend"] is not None
    ]

    if not items:
        continue

    best = max(items, key=lambda x: x["Trend"])
    worst = min(items, key=lambda x: x["Trend"])

    best_trends.append([
        category["Category"],
        best["Characteristic"],
        format_trend(best["Trend"])
    ])

    worst_trends.append([
        category["Category"],
        worst["Characteristic"],
        format_trend(worst["Trend"])
    ])


add_section(
    "8. Highest trend in each category",
    ["Category", "Characteristic", "Trend, %"],
    best_trends
)

add_section(
    "9. Lowest trend in each category",
    ["Category", "Characteristic", "Trend, %"],
    worst_trends
)


add_section(
    "10. Growing characteristics by category",
    ["Category", "Characteristic", "Trend, %", "Search volume"],
    sorted(
        trend_rows(growing),
        key=lambda x: (
            category_order.index(x[0]),
            -float(x[2].replace("%", ""))
        )
    )
)

add_section(
    "11. Declining characteristics by category",
    ["Category", "Characteristic", "Trend, %", "Search volume"],
    sorted(
        trend_rows(declining, reverse=False),
        key=lambda x: (
            category_order.index(x[0]),
            float(x[2].replace("%", ""))
        )
    )
)


best_competition = []
lowest_competition = []

for category in category_results:
    best = max(
        category["Items"],
        key=lambda x: x["Competition Number"]
    )

    worst = min(
        category["Items"],
        key=lambda x: x["Competition Number"]
    )

    best_competition.append([
        category["Category"],
        best["Characteristic"],
        best["Competing Products"],
        best["Competition Level"]
    ])

    lowest_competition.append([
        category["Category"],
        worst["Characteristic"],
        worst["Competing Products"],
        worst["Competition Level"]
    ])


add_section(
    "12. Most competitive characteristic in each category",
    ["Category", "Characteristic", "Competing products", "Competition level"],
    best_competition
)

add_section(
    "13. Least competitive characteristic in each category",
    ["Category", "Characteristic", "Competing products", "Competition level"],
    lowest_competition
)


add_section(
    "14. Categories with the highest competition",
    ["Category", "Competing products"],
    [
        [
            item["Category"],
            (">" if item["Competition Approximate"] else "")
            + f'{item["Competition"]:,}'
        ]
        for item in sorted(
            category_results,
            key=lambda x: -x["Competition"]
        )
    ]
)


with open(summary_file, "w", encoding="utf-8") as file:
    file.write("\n".join(summary))


print()
print(detail_table)

print()
print(f"Total groups: {len(results)}")
print(f"Detailed table: {output_file}")
print(f"Summary analysis: {summary_file}")
