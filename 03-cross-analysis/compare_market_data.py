
import csv
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parent.parent
results_folder = Path(__file__).resolve().parent / "results"
results_folder.mkdir(parents=True, exist_ok=True)

keyword_file = next((root / "01-keyword-analysis" / "data").glob("*.csv"))
product_file = next((root / "02-competitor-analysis" / "data").glob("*.csv"))

categories = {
    "Size": [
        "small", "large", "big", "mini",
        "4 inch", "5 inch", "6 inch",
        "7 inch", "8 inch", "10 inch"
    ],
    "Material": [
        "ceramic", "plastic", "terracotta"
    ],
    "Purpose": [
        "indoor", "outdoor", "house"
    ],
    "Functionality": [
        "drainage", "stand", "saucers", "smart"
    ],
    "Design": [
        "clear", "white", "black", "pink",
        "funny", "cute", "unique", "decorative",
        "boho", "tamagotchi", "peeing", "gepege"
    ],
    "Plant Type": [
        "snake", "spider"
    ]
}

stop_words = {
    "plant", "plants", "pot", "pots", "with",
    "for", "and", "the", "of", "a", "in"
}

feature_categories = {
    feature: category
    for category, features in categories.items()
    for feature in features
}

category_order = list(categories) + ["Other", "General", "Combined features"]


def number(value):
    value = str(value or "").strip()
    value = value.replace("\u00a0", "")
    value = value.replace(" ", "")
    value = value.replace(",", ".")
    value = value.replace("$", "").replace("%", "")

    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except ValueError:
        return None


def whole_number(value):
    value = str(value or "")
    value = value.replace("\u00a0", "")
    value = value.replace(" ", "")
    value = value.replace(",", "")
    value = value.replace(">", "").strip()

    try:
        return int(value)
    except ValueError:
        return None


def average(values):
    values = [value for value in values if value is not None]

    if not values:
        return None

    return sum(values) / len(values)


def display(value, decimals=1):
    if value is None:
        return "N/A"

    return f"{value:,.{decimals}f}"


def trend_display(value):
    if value is None:
        return "N/A"

    return f"{value:+g}%"


def make_table(headers, rows, group_index=None):
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

    previous_group = None

    for row in rows:
        if group_index is not None:
            group = row[group_index]

            if previous_group is not None and group != previous_group:
                lines.append("")

            previous_group = group

        lines.append(format_row(row))

    return "\n".join(lines)


def save_document(filename, sections):
    lines = []

    for title, headers, rows, group_index in sections:
        lines.append(title)
        lines.append("=" * len(title))
        lines.append(make_table(headers, rows, group_index))
        lines.append("")
        lines.append("")

    output_file = results_folder / filename

    with open(output_file, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def get_features(text):
    text = text.lower()

    sizes = re.findall(
        r"\b(\d+)\s*(?:inch|inches|in)\b",
        text
    )

    text = re.sub(
        r"\b\d+\s*(?:inch|inches|in)\b",
        " ",
        text
    )

    words = re.findall(r"[a-z]+", text)

    features = {
        word for word in words
        if word not in stop_words
    }

    for size in sizes:
        features.add(f"{size} inch")

    return features


def product_has_feature(title, feature):
    title = title.lower()

    alternatives = {
        "ceramic": r"\b(?:ceramic|stoneware|porcelain)\b",
        "terracotta": r"\b(?:terracotta|terra cotta)\b",
        "clear": r"\b(?:clear|transparent)\b",
        "drainage": r"\b(?:drainage|drain|draining)\b",
        "saucers": r"\b(?:saucer|saucers)\b",
        "stand": r"\b(?:stand|stands)\b",
        "house": r"\bhouse\s?plants?\b",
        "snake": r"\bsnake\s+plant\b",
        "spider": r"\bspider\s+plant\b"
    }

    if feature in alternatives:
        return bool(re.search(alternatives[feature], title))

    if feature.endswith(" inch"):
        size = feature.split()[0]

        pattern = (
            rf"(?<!\d){size}(?:\.0)?\s*"
            rf"(?:inch|inches|in\b|[\"”])"
        )

        return bool(re.search(pattern, title))

    return bool(re.search(rf"\b{re.escape(feature)}\b", title))


def get_group(value, limits, labels):
    if value is None:
        return "N/A"

    for limit, label in zip(limits, labels):
        if value < limit:
            return label

    return labels[-1]


def group_products(products, selector):
    groups = defaultdict(list)

    for product in products:
        group = selector(product)

        if group != "N/A":
            groups[str(group)].append(product)

    return groups


def group_table(groups):
    rows = []

    for name, items in groups.items():
        rows.append([
            name,
            len(items),
            display(sum(p["sales"] or 0 for p in items), 0),
            display(average(p["sales"] for p in items)),
            display(average(p["price"] for p in items), 2),
            display(average(p["rating"] for p in items), 2)
        ])

    rows.sort(
        key=lambda row: -float(row[3].replace(",", ""))
    )

    return rows


group_headers = [
    "Group",
    "Products",
    "Total units",
    "Avg units",
    "Avg price, $",
    "Avg rating"
]


with open(keyword_file, encoding="utf-8-sig", newline="") as file:
    keywords = list(csv.DictReader(file))

with open(product_file, encoding="utf-8-sig", newline="") as file:
    products = list(csv.DictReader(file))


fields = {
    "price": "Price  USD",
    "sales": "ASIN Sales",
    "revenue": "ASIN Revenue",
    "fees": "Fees  USD",
    "rating": "Ratings",
    "reviews": "Review Count",
    "review_velocity": "Review velocity",
    "images": "Images",
    "title_length": "Title Char. Count",
    "active_sellers": "Active Sellers",
    "seller_age": "Seller Age (mo)",
    "weight": "Weight",
    "bsr": "BSR"
}

for product in products:
    for key, column in fields.items():
        product[key] = number(product[column])

    product["brand"] = product["Brand"].strip() or "Unknown"

    product["sponsored"] = (
        "Yes" if product["Sponsored"].strip() else "No"
    )

    product["best_seller"] = (
        "Yes" if product["Best Seller"].strip().lower() == "yes"
        else "No"
    )

    product["amazon_seller"] = (
        "Yes" if product["Seller"].strip().lower() == "amazon"
        else "No"
    )

    product["amazon_buybox"] = (
        "Yes" if product["Buy Box"].strip().lower() == "amazon"
        else "No"
    )

    try:
        date = datetime.strptime(
            product["Creation Date"].strip(),
            "%b %d, %Y"
        )

        product["listing_age"] = max(
            0,
            (datetime.now() - date).days / 30.44
        )

    except ValueError:
        product["listing_age"] = None

    dimensions = [
        number(value)
        for value in re.findall(
            r"\d+(?:[.,]\d+)?",
            product["Dimensions"]
        )
    ]

    if len(dimensions) >= 3:
        product["volume"] = math.prod(dimensions[:3])
    else:
        product["volume"] = None


all_features = set(feature_categories)

for keyword in keywords:
    all_features.update(
        get_features(keyword["Keyword Phrase"])
    )


feature_results = []

for feature in all_features:
    matched_keywords = [
        keyword for keyword in keywords
        if feature in get_features(keyword["Keyword Phrase"])
    ]

    matched_products = [
        product for product in products
        if product_has_feature(
            product["Product Details"],
            feature
        )
    ]

    trends = [
        number(keyword["Search Volume Trend, %"])
        for keyword in matched_keywords
    ]

    total_trend = (
        sum(trends)
        if trends and all(t is not None for t in trends)
        else None
    )

    competition = sum(
        whole_number(keyword["Competing Products"]) or 0
        for keyword in matched_keywords
    )

    approximate = any(
        ">" in keyword["Competing Products"]
        for keyword in matched_keywords
    )

    competition_text = (
        (">" if approximate else "")
        + display(competition, 0)
    )

    feature_results.append({
        "category": feature_categories.get(feature, "Other"),
        "feature": feature,
        "keywords": len(matched_keywords),
        "searches": sum(
            whole_number(keyword["Search Volume, q./last month"]) or 0
            for keyword in matched_keywords
        ),
        "trend": total_trend,
        "competition": competition_text,
        "products": len(matched_products),
        "sales": sum(
            product["sales"] or 0
            for product in matched_products
        ),
        "revenue": sum(
            product["revenue"] or 0
            for product in matched_products
        ),
        "price": average(
            product["price"] for product in matched_products
        ),
        "rating": average(
            product["rating"] for product in matched_products
        )
    })


feature_results.sort(
    key=lambda item: (
        category_order.index(item["category"]),
        -item["sales"],
        -item["searches"]
    )
)


feature_headers = [
    "Category",
    "Characteristic",
    "Keywords",
    "Searches",
    "Sum trends, %",
    "Competing products",
    "Products",
    "Units sold",
    "Revenue, $",
    "Avg price, $",
    "Avg rating"
]

feature_rows = [
    [
        item["category"],
        item["feature"],
        item["keywords"],
        display(item["searches"], 0),
        trend_display(item["trend"]),
        item["competition"],
        item["products"],
        display(item["sales"], 0),
        display(item["revenue"], 2),
        display(item["price"], 2),
        display(item["rating"], 2)
    ]
    for item in feature_results
]


keyword_rows = []

for keyword in keywords:
    phrase = keyword["Keyword Phrase"]
    features = get_features(phrase)

    matched = [
        product for product in products
        if features and all(
            product_has_feature(
                product["Product Details"],
                feature
            )
            for feature in features
        )
    ]

    matched_sales = sum(
        product["sales"] or 0
        for product in matched
    )

    if not features:
        category = "General"
    elif len(features) == 1:
        category = feature_categories.get(
            next(iter(features)),
            "Other"
        )
    else:
        category = "Combined features"

    keyword_rows.append([
        category,
        phrase,
        display(
            whole_number(keyword["Search Volume, q./last month"]),
            0
        ),
        keyword["Search Volume Trend, %"],
        keyword["Competing Products"],
        len(matched),
        display(matched_sales, 0),
        matched_sales
    ])

keyword_rows.sort(
    key=lambda row: (
        category_order.index(row[0]),
        -row[-1]
    )
)

keyword_rows = [row[:-1] for row in keyword_rows]


save_document(
    "01-demand-vs-sales.txt",
    [
        (
            "All characteristics sorted by units sold",
            feature_headers,
            feature_rows,
            0
        ),
        (
            "All search phrases and matching products",
            [
                "Category",
                "Search phrase",
                "Searches",
                "Trend, %",
                "Competition",
                "Products",
                "Units sold"
            ],
            keyword_rows,
            0
        )
    ]
)


price_groups = group_products(
    products,
    lambda p: get_group(
        p["price"],
        [10, 20, 30, 50, float("inf")],
        [
            "< $10",
            "$10–19.99",
            "$20–29.99",
            "$30–49.99",
            "$50+"
        ]
    )
)

save_document(
    "02-price-analysis.txt",
    [
        (
            "Sales by price range",
            group_headers,
            group_table(price_groups),
            None
        )
    ]
)


review_groups = group_products(
    products,
    lambda p: get_group(
        p["reviews"],
        [100, 500, 1000, 5000, float("inf")],
        [
            "<100",
            "100–499",
            "500–999",
            "1,000–4,999",
            "5,000+"
        ]
    )
)

rating_groups = group_products(
    products,
    lambda p: get_group(
        p["rating"],
        [4, 4.5, 4.8, float("inf")],
        [
            "<4.0",
            "4.0–4.49",
            "4.5–4.79",
            "4.8+"
        ]
    )
)

velocity_groups = group_products(
    products,
    lambda p: get_group(
        p["review_velocity"],
        [10, 50, 100, float("inf")],
        [
            "<10",
            "10–49",
            "50–99",
            "100+"
        ]
    )
)

save_document(
    "03-reviews-and-ratings.txt",
    [
        (
            "Sales by review count",
            group_headers,
            group_table(review_groups),
            None
        ),
        (
            "Sales by rating",
            group_headers,
            group_table(rating_groups),
            None
        ),
        (
            "Sales by review velocity",
            group_headers,
            group_table(velocity_groups),
            None
        )
    ]
)


brand_groups = group_products(
    products,
    lambda p: p["brand"]
)

brand_rows = []

for brand, items in brand_groups.items():
    brand_rows.append([
        brand,
        len(items),
        display(
            sum(p["sales"] or 0 for p in items),
            0
        ),
        display(average(p["sales"] for p in items)),
        display(average(p["reviews"] for p in items)),
        display(average(p["rating"] for p in items), 2)
    ])

brand_rows.sort(
    key=lambda row: -float(row[2].replace(",", ""))
)


save_document(
    "04-brand-and-advertising.txt",
    [
        (
            "Sales by brand",
            [
                "Brand",
                "Products",
                "Total units",
                "Avg units",
                "Avg reviews",
                "Avg rating"
            ],
            brand_rows,
            None
        ),
        (
            "Sponsored vs non-sponsored",
            group_headers,
            group_table(
                group_products(
                    products,
                    lambda p: p["sponsored"]
                )
            ),
            None
        ),
        (
            "Sales by fulfillment",
            group_headers,
            group_table(
                group_products(
                    products,
                    lambda p: p["Fulfillment"] or "N/A"
                )
            ),
            None
        ),
        (
            "Amazon Buy Box vs other",
            group_headers,
            group_table(
                group_products(
                    products,
                    lambda p: p["amazon_buybox"]
                )
            ),
            None
        ),
        (
            "Amazon seller vs other",
            group_headers,
            group_table(
                group_products(
                    products,
                    lambda p: p["amazon_seller"]
                )
            ),
            None
        ),
        (
            "Sales by seller country or region",
            group_headers,
            group_table(
                group_products(
                    products,
                    lambda p: p["Seller Country/Region"]
                )
            ),
            None
        )
    ]
)


listing_groups = group_products(
    products,
    lambda p: get_group(
        p["listing_age"],
        [6, 12, 36, float("inf")],
        [
            "<6 months",
            "6–11 months",
            "12–35 months",
            "36+ months"
        ]
    )
)

image_groups = group_products(
    products,
    lambda p: get_group(
        p["images"],
        [4, 7, 10, float("inf")],
        [
            "0–3",
            "4–6",
            "7–9",
            "10+"
        ]
    )
)

title_groups = group_products(
    products,
    lambda p: get_group(
        p["title_length"],
        [100, 150, 200, float("inf")],
        [
            "<100",
            "100–149",
            "150–199",
            "200+"
        ]
    )
)

save_document(
    "05-listing-performance.txt",
    [
        (
            "Sales by listing age",
            group_headers,
            group_table(listing_groups),
            None
        ),
        (
            "Sales by number of images",
            group_headers,
            group_table(image_groups),
            None
        ),
        (
            "Sales by title length",
            group_headers,
            group_table(title_groups),
            None
        ),
        (
            "Sales by Best Seller badge",
            group_headers,
            group_table(
                group_products(
                    products,
                    lambda p: p["best_seller"]
                )
            ),
            None
        )
    ]
)


logistic_groups = {
    "Size tier": lambda p: p["Size Tier"] or "N/A",

    "Weight": lambda p: get_group(
        p["weight"],
        [1, 3, 5, float("inf")],
        ["<1", "1–2.99", "3–4.99", "5+"]
    ),

    "Dimensions volume": lambda p: get_group(
        p["volume"],
        [200, 500, 1000, float("inf")],
        ["<200", "200–499", "500–999", "1,000+"]
    ),

    "Active sellers": lambda p: get_group(
        p["active_sellers"],
        [2, 4, float("inf")],
        ["1", "2–3", "4+"]
    ),

    "Amazon fees": lambda p: get_group(
        p["fees"],
        [5, 10, 20, float("inf")],
        ["<$5", "$5–9.99", "$10–19.99", "$20+"]
    ),

    "Seller age": lambda p: get_group(
        p["seller_age"],
        [12, 36, 60, float("inf")],
        ["<12 months", "12–35 months", "36–59 months", "60+"]
    )
}

logistic_sections = []

for name, selector in logistic_groups.items():
    logistic_sections.append((
        f"Sales by {name.lower()}",
        group_headers,
        group_table(group_products(products, selector)),
        None
    ))

save_document(
    "06-product-and-logistics.txt",
    logistic_sections
)


factor_groups = {
    "Price": lambda p: get_group(
        p["price"],
        [10, 20, 30, 50, float("inf")],
        ["<$10", "$10–19.99", "$20–29.99", "$30–49.99", "$50+"]
    ),

    "Rating": lambda p: get_group(
        p["rating"],
        [4, 4.5, 4.8, float("inf")],
        ["<4", "4–4.49", "4.5–4.79", "4.8+"]
    ),

    "Review count": lambda p: get_group(
        p["reviews"],
        [100, 500, 1000, 5000, float("inf")],
        ["<100", "100–499", "500–999", "1,000–4,999", "5,000+"]
    ),

    "Review velocity": lambda p: get_group(
        p["review_velocity"],
        [10, 50, 100, float("inf")],
        ["<10", "10–49", "50–99", "100+"]
    ),

    "Sponsored": lambda p: p["sponsored"],

    "Brand": lambda p: p["brand"],

    "Fulfillment": lambda p: p["Fulfillment"],

    "Amazon Buy Box": lambda p: p["amazon_buybox"],

    "Amazon seller": lambda p: p["amazon_seller"],

    "Seller country": lambda p: p["Seller Country/Region"],

    "Best Seller badge": lambda p: p["best_seller"],

    "Images": lambda p: get_group(
        p["images"],
        [4, 7, 10, float("inf")],
        ["0–3", "4–6", "7–9", "10+"]
    ),

    "Title length": lambda p: get_group(
        p["title_length"],
        [100, 150, 200, float("inf")],
        ["<100", "100–149", "150–199", "200+"]
    ),

    "Listing age": lambda p: get_group(
        p["listing_age"],
        [6, 12, 36, float("inf")],
        ["<6m", "6–11m", "12–35m", "36m+"]
    ),

    "Seller age": lambda p: get_group(
        p["seller_age"],
        [12, 36, 60, float("inf")],
        ["<12m", "12–35m", "36–59m", "60m+"]
    ),

    "Active sellers": lambda p: get_group(
        p["active_sellers"],
        [2, 4, float("inf")],
        ["1", "2–3", "4+"]
    ),

    "Weight": lambda p: get_group(
        p["weight"],
        [1, 3, 5, float("inf")],
        ["<1", "1–2.99", "3–4.99", "5+"]
    ),

    "Dimensions volume": lambda p: get_group(
        p["volume"],
        [200, 500, 1000, float("inf")],
        ["<200", "200–499", "500–999", "1,000+"]
    ),

    "Size tier": lambda p: p["Size Tier"],

    "Fees": lambda p: get_group(
        p["fees"],
        [5, 10, 20, float("inf")],
        ["<$5", "$5–9.99", "$10–19.99", "$20+"]
    )
}


factor_rows = []

for factor, selector in factor_groups.items():
    groups = group_products(products, selector)

    valid_groups = [
        (name, items)
        for name, items in groups.items()
        if len(items) >= 3
    ]

    if len(valid_groups) < 2:
        factor_rows.append([
            factor,
            "Insufficient data",
            "",
            "",
            "",
            "",
            ""
        ])
        continue

    best_name, best_items = max(
        valid_groups,
        key=lambda group: average(
            p["sales"] for p in group[1]
        ) or 0
    )

    worst_name, worst_items = min(
        valid_groups,
        key=lambda group: average(
            p["sales"] for p in group[1]
        ) or 0
    )

    factor_rows.append([
        factor,
        best_name,
        len(best_items),
        display(average(p["sales"] for p in best_items)),
        worst_name,
        len(worst_items),
        display(average(p["sales"] for p in worst_items))
    ])


best_features = []

for category in categories:
    items = [
        item for item in feature_results
        if item["category"] == category
        and item["products"] > 0
    ]

    if not items:
        continue

    best = max(
        items,
        key=lambda item: item["sales"]
    )

    best_features.append([
        category,
        best["feature"],
        best["products"],
        display(best["sales"], 0),
        display(best["searches"], 0),
        trend_display(best["trend"])
    ])


brand_winner = max(
    brand_groups.items(),
    key=lambda group: sum(
        product["sales"] or 0
        for product in group[1]
    )
)

product_leader = max(
    products,
    key=lambda product: product["sales"] or 0
)


leader_rows = [
    [
        "Best-selling product",
        product_leader["Product Details"]
    ],
    [
        "Product brand",
        product_leader["brand"]
    ],
    [
        "Product sales",
        display(product_leader["sales"], 0)
    ],
    [
        "Best-selling brand",
        brand_winner[0]
    ],
    [
        "Brand sales",
        display(
            sum(
                product["sales"] or 0
                for product in brand_winner[1]
            ),
            0
        )
    ]
]


save_document(
    "07-factor-summary.txt",
    [
        (
            "Best-selling characteristic in each category",
            [
                "Category",
                "Characteristic",
                "Products",
                "Units sold",
                "Searches",
                "Sum trends, %"
            ],
            best_features,
            None
        ),
        (
            "Best and worst groups by average sales",
            [
                "Factor",
                "Best group",
                "Products",
                "Avg units",
                "Lowest group",
                "Products",
                "Avg units"
            ],
            factor_rows,
            None
        ),
        (
            "Overall market leaders",
            ["Metric", "Value"],
            leader_rows,
            None
        )
    ]
)


print("Cross-analysis completed.")
print()

for file in sorted(results_folder.glob("*.txt")):
    print(file.relative_to(root))
