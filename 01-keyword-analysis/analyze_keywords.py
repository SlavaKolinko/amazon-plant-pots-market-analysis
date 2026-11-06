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


def get_competition_level(value, approximate=False):
    """Levels based on a reported value or a strict lower bound, not a sum."""
    if value >= 20000:
        return "High"
    if approximate:
        return "At least Medium" if value >= 5000 else "Unknown"
    if value < 5000:
        return "Low"
    return "Medium"


def calculate_group_trend(comparable_current, previous_volume):
    """Aggregate percentage change over comparable rows only."""
    if previous_volume <= 0:
        return None
    return (comparable_current / previous_volume - 1) * 100


def format_competition(number, approximate):
    return (">" if approximate else "") + f"{number:,}"


def format_trend(value):
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"


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
    comparable_current = 0
    previous_volume = 0.0
    valid_trends = 0
    competition_number = None
    competition_approximate = False

    for row in rows:
        volume = get_number(row["Search Volume, q./last month"])
        trend = get_trend(row["Search Volume Trend, %"])
        competition_text = row["Competing Products"].strip()
        competitor_count = get_number(competition_text)
        competitor_is_lower_bound = ">" in competition_text

        total_volume += volume

        # Percent changes are NOT additive. Reconstruct comparable prior volumes.
        # Missing or invalid trends remain in the total demand, but not trend calculations.
        if trend is not None and trend > -100:
            comparable_current += volume
            previous_volume += volume / (1 + trend / 100)
            valid_trends += 1

        # This is the maximum REPORTED observation, NOT a unique product count.
        if competition_number is None or competitor_count > competition_number:
            competition_number = competitor_count
            competition_approximate = competitor_is_lower_bound
        elif competitor_count == competition_number and competitor_is_lower_bound:
            competition_approximate = True

    if competition_number is None:
        competition_number = 0

    grouped_trend = calculate_group_trend(comparable_current, previous_volume)

    results.append({
        "Category": category,
        "Characteristic": characteristic,
        "Keywords": len(rows),
        "Search Volume": total_volume,
        "Comparable Current Volume": comparable_current,
        "Previous Volume": previous_volume,
        "Valid Trends": valid_trends,
        "Trend": grouped_trend,
        "Competing Products": format_competition(competition_number, competition_approximate),
        "Competition Number": competition_number,
        "Competition Approximate": competition_approximate,
        "Competition Level": get_competition_level(competition_number, competition_approximate)
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
    "Max reported competition",
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

    category_comparable_current = sum(item["Comparable Current Volume"] for item in items)
    category_previous = sum(item["Previous Volume"] for item in items)
    category_competition_number = max(item["Competition Number"] for item in items)
    # If the maximum is reported with '>', retain that uncertainty.
    category_competition_approximate = any(
        item["Competition Number"] == category_competition_number
        and item["Competition Approximate"]
        for item in items
    )

    category_results.append({
        "Category": category,
        "Search Volume": sum(item["Search Volume"] for item in items),
        "Trend": calculate_group_trend(category_comparable_current, category_previous),
        "Comparable Current Volume": category_comparable_current,
        "Previous Volume": category_previous,
        "Competition": category_competition_number,
        "Competition Approximate": category_competition_approximate,
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
    "6. Categories with the highest aggregated trend",
    ["Category", "Aggregated trend, %"],
    [
        [item["Category"], format_trend(item["Trend"])]
        for item in sorted(
            valid_categories,
            key=lambda x: -x["Trend"]
        )
    ]
)

add_section(
    "7. Categories with the lowest aggregated trend",
    ["Category", "Aggregated trend, %"],
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
    ["Category", "Characteristic", "Max reported competition", "Competition level"],
    best_competition
)

add_section(
    "13. Least competitive characteristic in each category",
    ["Category", "Characteristic", "Max reported competition", "Competition level"],
    lowest_competition
)


add_section(
    "14. Categories with the highest max reported competition",
    ["Category", "Max reported competition"],
    [
        [
            item["Category"],
            format_competition(item["Competition"], item["Competition Approximate"])
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
