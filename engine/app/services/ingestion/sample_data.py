"""In-memory sample data generator for NOVEM.

Generates realistic e-commerce DataFrames directly — no CSV files needed.
All dates are relative to today, so data is always fresh.
Works in both development and frozen (PyInstaller) mode.
"""

import hashlib
import logging
import random
from datetime import datetime, timedelta, timezone

import pandas as pd

logger = logging.getLogger(__name__)

SEED = 42

# ── Volume knobs ────────────────────────────────────────────────────────

NUM_ORDERS = 50_000
NUM_CUSTOMERS = 5_000
NUM_REVIEWS = 6_000
AD_SPEND_DAYS = 548  # ~18 months
STOCK_SNAPSHOT_WEEKS = 78  # ~18 months

# ── Product catalog ─────────────────────────────────────────────────────

CATEGORIES: dict[str, list[tuple[str, int]]] = {
    "Electronics": [
        ("Wireless Earbuds", 1499), ("Bluetooth Speaker", 2499), ("USB-C Hub", 1899),
        ("Mechanical Keyboard", 3999), ("Gaming Mouse", 1299), ("Webcam HD", 2199),
        ("Portable Charger", 999), ("Smart Watch", 7999), ("NC Headphones", 5999),
        ("LED Monitor 27\"", 14999), ("Tablet Stand", 799), ("HDMI Cable 6ft", 349),
        ("Wireless Charger Pad", 1199), ("Power Strip Surge", 899), ("Ring Light Kit", 1499),
        ("External SSD 1TB", 5499), ("Smart Plug WiFi", 699), ("Laptop Cooling Pad", 1299),
        ("Dash Cam 4K", 4999), ("Portable Projector", 8999),
        ("USB Microphone", 2999), ("Bluetooth Adapter", 499), ("Smart Doorbell", 3499),
        ("WiFi Extender", 1799), ("Drone Mini", 6999),
        ("VR Headset", 24999), ("Noise Machine", 1999), ("eReader Case", 599),
        ("Smart Scale", 2499), ("Action Camera", 12999),
    ],
    "Clothing": [
        ("Classic Crew T-Shirt", 599), ("Slim Fit Jeans", 1499), ("Lightweight Hoodie", 1299),
        ("Bomber Jacket", 2499), ("Cotton Polo", 799), ("Chino Pants", 1199),
        ("Denim Jacket", 1999), ("Running Shorts", 699), ("Wool Cardigan", 1799),
        ("Flannel Shirt", 999), ("Graphic Tee", 499), ("Cargo Joggers", 1099),
        ("Puffer Vest", 1499), ("V-Neck Sweater", 1299), ("Maxi Dress", 1599),
        ("Linen Blazer", 2999), ("Sports Bra", 699), ("Yoga Leggings", 899),
        ("Raincoat Packable", 1799), ("Silk Scarf", 999),
        ("Formal Shirt", 1299), ("Leather Belt", 799), ("Wool Overcoat", 4999),
        ("Swim Trunks", 699), ("Thermal Socks Pack", 399),
        ("Beanie Cap", 349), ("Track Pants", 899), ("Kurta Set", 1499),
        ("Sherwani", 5999), ("Saree Silk", 3999),
    ],
    "Home & Kitchen": [
        ("Stainless Steel Blender", 2999), ("Ceramic Knife Set", 1999), ("Cast Iron Skillet", 1599),
        ("Air Fryer 5qt", 4999), ("French Press Coffee", 1199), ("Bamboo Cutting Board", 799),
        ("Silicone Spatula Set", 499), ("Glass Storage Containers", 899), ("Electric Kettle", 1499),
        ("Dish Drying Rack", 999), ("Spice Rack Organizer", 599), ("Nonstick Pan Set", 2499),
        ("Hand Mixer", 1299), ("Wine Opener Set", 699), ("Tea Infuser Bottle", 499),
        ("Vacuum Insulated Mug", 799), ("Compost Bin", 1199), ("Ice Cube Tray Silicone", 299),
        ("Salad Spinner", 699), ("Kitchen Scale Digital", 599),
        ("Instant Pot 6qt", 5999), ("Toaster Oven", 3499), ("Immersion Blender", 1499),
        ("Pressure Cooker", 2999), ("Spice Grinder", 899),
        ("Rice Cooker", 1999), ("Mandoline Slicer", 799), ("Baking Sheet Set", 699),
        ("Coffee Grinder", 1799), ("Mortar Pestle Marble", 599),
    ],
    "Books": [
        ("The Data Warehouse Toolkit", 499), ("Atomic Habits", 399), ("Clean Code", 549),
        ("Designing Data-Intensive Apps", 599), ("The Lean Startup", 449), ("Deep Work", 399),
        ("Python Crash Course", 549), ("Sapiens", 499), ("Thinking Fast and Slow", 449),
        ("The Pragmatic Programmer", 599), ("Zero to One", 399), ("Hooked", 349),
        ("Influence Psychology", 449), ("The Art of War", 199), ("Meditations", 249),
        ("Essentialism", 349), ("The Phoenix Project", 449), ("Good to Great", 399),
        ("Never Split the Difference", 399), ("Originals", 349),
        ("Start with Why", 399), ("Ikigai", 299), ("Rich Dad Poor Dad", 349),
        ("The Alchemist", 299), ("Bhagavad Gita", 199),
        ("Wings of Fire", 349), ("The Monk Who Sold His Ferrari", 299),
        ("Gitanjali", 249), ("Midnight's Children", 449), ("Train to Pakistan", 299),
    ],
    "Sports & Outdoors": [
        ("Yoga Mat Premium", 1299), ("Resistance Band Set", 699), ("Foam Roller", 899),
        ("Jump Rope Speed", 399), ("Dumbbell Adjustable", 2499), ("Pull-Up Bar Doorway", 1499),
        ("Running Belt Waist", 499), ("Insulated Water Bottle", 699), ("Camping Hammock", 1799),
        ("Hiking Backpack 40L", 2999), ("Tennis Racket", 1999), ("Soccer Ball Size 5", 899),
        ("Bike Phone Mount", 599), ("Swim Goggles", 499), ("Fitness Tracker Band", 1499),
        ("Climbing Chalk Bag", 399), ("Boxing Gloves", 1299), ("Ab Roller Wheel", 599),
        ("Ankle Weights 5lb", 699), ("Compression Socks", 499),
        ("Treadmill Foldable", 19999), ("Kettlebell Cast Iron", 1799),
        ("Badminton Racket Pro", 1299), ("Cricket Bat Kashmir", 3499), ("Carrom Board Full", 2499),
        ("Table Tennis Set", 999), ("Skipping Rope Digital", 599),
        ("Gym Bag Duffel", 999), ("Protein Shaker", 349), ("Wrist Wraps", 299),
    ],
    "Beauty & Personal Care": [
        ("Vitamin C Serum", 799), ("Retinol Moisturizer", 999), ("Hyaluronic Acid Serum", 899),
        ("Sunscreen SPF 50", 499), ("Charcoal Face Mask", 399), ("Jade Roller Set", 699),
        ("Hair Growth Oil", 599), ("Dry Shampoo", 449), ("Electric Toothbrush", 1999),
        ("Teeth Whitening Kit", 1499), ("Beard Grooming Kit", 899), ("Lip Balm Set", 299),
        ("Body Lotion Shea", 499), ("Nail Polish Set", 399), ("Perfume Sampler", 1299),
        ("Facial Cleansing Brush", 1499), ("Eye Cream Anti-Aging", 799), ("Collagen Powder", 1199),
        ("Dead Sea Salt Scrub", 699), ("Aromatherapy Diffuser", 1499),
        ("Turmeric Face Cream", 349), ("Coconut Oil Cold-Pressed", 299),
        ("Aloe Vera Gel Organic", 249), ("Neem Face Wash", 199), ("Kajal Waterproof", 149),
        ("Hair Serum Argan", 599), ("Rose Water Toner", 199),
        ("Shaving Kit Premium", 999), ("Henna Powder Natural", 149), ("Kumkumadi Tailam", 499),
    ],
    "Toys & Games": [
        ("LEGO Architecture Set", 2999), ("Board Game Strategy", 1299), ("Puzzle 1000pc", 699),
        ("RC Drone Mini", 1999), ("Building Blocks Set", 899), ("Card Game Party", 399),
        ("Science Kit Kids", 1199), ("Action Figure Collector", 999), ("Dollhouse Wooden", 2499),
        ("Remote Control Car", 1499), ("Magic Kit Beginner", 599), ("Nerf Blaster", 1299),
        ("Play-Doh Mega Pack", 699), ("Marble Run Set", 999), ("Coding Robot Kit", 2999),
        ("Art Supply Kit", 799), ("Telescope Kids", 1799), ("Microscope Set", 1499),
        ("Chess Set Wooden", 599), ("Bubble Machine", 399),
        ("Rubik's Cube Speed", 299), ("Ludo Board Classic", 199),
        ("Snakes Ladders Wooden", 249), ("Train Set Electric", 1999),
        ("Sand Art Kit", 349), ("Puppet Theater", 1299), ("Kite Fighter", 99),
        ("Spinning Top Metal", 149), ("Kaleidoscope", 199), ("Origami Paper Set", 249),
    ],
    "Pet Supplies": [
        ("Automatic Pet Feeder", 2499), ("Cat Tree Tower", 3499), ("Dog Harness No-Pull", 899),
        ("Pet Water Fountain", 1499), ("Dog Bed Orthopedic", 1999), ("Cat Litter Mat", 699),
        ("Interactive Dog Toy", 599), ("Pet Grooming Kit", 1199), ("Fish Tank Filter", 899),
        ("Bird Cage Large", 2999), ("Dog Training Treats", 399), ("Cat Scratching Post", 799),
        ("Pet Carrier Airline", 1999), ("Dog Raincoat", 699), ("Catnip Toy Set", 299),
        ("Aquarium LED Light", 799), ("Dog Poop Bag Holder", 199), ("Pet Nail Trimmer", 499),
        ("Hamster Wheel Silent", 399), ("Reptile Heat Lamp", 699),
        ("Dog Leash Retractable", 599), ("Cat Food Premium 5kg", 1299),
        ("Dog Shampoo Organic", 349), ("Bird Seed Mix 2kg", 299),
        ("Aquarium Plants Set", 499), ("Parrot Perch Stand", 899),
        ("Rabbit Hutch", 2499), ("Turtle Basking Dock", 349),
        ("Flea Collar Adjustable", 249), ("Pet GPS Tracker", 1999),
    ],
}

CHANNELS = ["organic", "google_ads", "meta_ads", "email", "tiktok", "referral", "direct", "affiliate"]
REGIONS = [
    "IN-North", "IN-South", "IN-West", "IN-East", "IN-Central",
    "US-East", "US-West", "UK", "Germany", "Canada", "Australia",
    "UAE", "Singapore", "Japan", "France",
]

STATUSES_WEIGHTED = (
    ["completed"] * 72 + ["pending"] * 8 + ["processing"] * 6
    + ["refunded"] * 8 + ["cancelled"] * 6
)

REFUND_REASONS = [
    "Item damaged during shipping", "Wrong size/color received",
    "Product not as described", "Changed mind", "Found cheaper elsewhere",
    "Arrived too late", "Defective product", "Duplicate order",
    "Missing parts", "Allergic reaction",
]

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Shaurya", "Atharva", "Advait", "Dhruv", "Kabir",
    "Ananya", "Diya", "Myra", "Sara", "Aanya", "Aadhya", "Aarohi", "Anvi",
    "Prisha", "Riya", "Saanvi", "Aisha", "Navya", "Pari", "Zara",
    "Rahul", "Priya", "Amit", "Neha", "Vikram", "Pooja", "Raj", "Meera",
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "David", "Elizabeth", "William", "Barbara",
    "Wei", "Carlos", "Yuki", "Omar", "Hans", "Pierre", "Fatima", "Amara",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Reddy", "Nair",
    "Iyer", "Joshi", "Agarwal", "Malhotra", "Chopra", "Kapoor", "Mehta",
    "Das", "Bose", "Mukherjee", "Chatterjee", "Banerjee",
    "Khan", "Shah", "Rao", "Pillai", "Menon", "Desai", "Thakur", "Pandey",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Wilson", "Anderson",
    "Lee", "Chen", "Kim", "Tanaka", "Muller", "Dubois",
]

REVIEW_POSITIVE = [
    "Absolutely love this product! The build quality is exceptional and it arrived well-packaged. Would definitely recommend to anyone looking for a reliable option in this price range.",
    "Five stars! Exceeded my expectations in every way. The material feels premium and the functionality is top-notch. My whole family loves it.",
    "Best purchase I've made this year. Super fast delivery to Mumbai and the product works exactly as described. The color is even better in person.",
    "Value for money at its finest. I compared multiple options on Amazon and Flipkart before choosing this one, and I'm glad I did. Outstanding quality.",
    "Impressive quality for the price point. I was skeptical at first but this product really delivers. Highly recommended for daily use.",
    "Perfect gift! Bought this for my sister's birthday and she absolutely loves it. Great packaging and presentation.",
    "Using it for 3 months now and still going strong. No deterioration in quality whatsoever. Will definitely buy from this brand again.",
    "The customer service was incredibly helpful when I had a question. Product itself is amazing — sturdy, well-designed, and functional.",
    "Pleasantly surprised by the attention to detail. Even the packaging was eco-friendly which I really appreciate.",
    "This is my third purchase from this brand and they never disappoint. Consistent quality across all their products.",
    "Works like a charm! Set it up in 5 minutes and it's been running flawlessly. The instructions were clear and easy to follow.",
    "Bought this during the Diwali sale and got a great deal. The product quality is way above what I expected for the discounted price.",
    "Excellent craftsmanship. You can tell a lot of thought went into designing this. Very ergonomic and comfortable to use daily.",
    "My go-to recommendation whenever friends ask for suggestions. I've already convinced 4 people to buy this!",
]

REVIEW_NEUTRAL = [
    "It's okay for the price. Nothing extraordinary but gets the job done. The build could be slightly better.",
    "Decent product. Meets basic needs but I was hoping for a bit more features at this price point. Average experience overall.",
    "Product arrived on time and works as expected. Not blown away but not disappointed either. Standard quality.",
    "Does what it says on the box. No more, no less. Packaging was basic but the product is functional.",
    "Average quality. I've seen better and I've seen worse. It serves its purpose well enough for casual use.",
    "The product is fine for occasional use. Wouldn't rely on it for heavy daily use though. Middle of the road.",
    "Received the item in good condition. It's a standard product, nothing premium about it but acceptable for the price.",
    "Mixed feelings. Some features work great while others feel underdeveloped. Could use some improvements.",
]

REVIEW_NEGATIVE = [
    "Very disappointed with this purchase. The quality is nowhere near what was advertised. Feels cheap and flimsy.",
    "Arrived damaged and customer support took forever to respond. Had to follow up three times before getting a resolution.",
    "Not worth the money at all. Broke within two weeks of normal use. Clearly poor manufacturing quality.",
    "Product looks nothing like the pictures. Color is completely off and the material feels scratchy and uncomfortable.",
    "Terrible experience. The item was used/returned before and sent to me as new. Had stains and missing parts.",
    "Stopped working after just one month. Very poor durability for the price. Would not buy again.",
    "The sizing is completely wrong. Ordered M but received something that fits like XS. Very frustrating return process.",
    "Packaging was damaged and the product inside was scratched. No quality control at all.",
    "Allergic reaction after first use. The materials clearly contain something not listed in the ingredients.",
    "Complete waste of money. The product is nothing like described. I want a full refund immediately.",
]

REVIEW_EXTRAS = [
    " Delivery was quick to Bengaluru.",
    " Slightly smaller than expected but still good.",
    " Packaging could be improved.",
    " Would make a great Diwali gift.",
    " Price increased since I last checked.",
    " COD option was convenient.",
    " Compared with local market prices, this is a steal.",
    " The quality matches what you'd find at Reliance Digital.",
]

CAMPAIGN_NAMES = {
    "google_ads": [
        "Brand_Search_IN", "Shopping_Electronics", "Shopping_Clothing",
        "Performance_Max_All", "Display_Remarketing", "YouTube_Brand",
        "Search_Generic_Home", "Shopping_Books", "Search_Competitors",
        "Shopping_Home_Decor", "Search_Tech_Deals",
    ],
    "meta_ads": [
        "FB_Lookalike_1pct", "FB_Retarget_Cart", "IG_Stories_Brand",
        "FB_Broad_Electronics", "IG_Reels_Fashion", "FB_DPA_Catalog",
        "FB_Engagement_Posts", "IG_Shopping_Feed",
        "FB_Home_Furniture_Sale", "IG_Book_Club_Promo",
    ],
    "tiktok": [
        "TT_TopView_Launch", "TT_InFeed_Sale", "TT_Spark_UGC",
        "TT_Collection_Gadgets", "TT_Branded_Challenge",
        "TT_Fashion_Haul", "TT_Home_Makeover",
    ],
    "email": [
        "Weekly_Newsletter", "Abandoned_Cart_Flow", "Win_Back_30d",
        "Welcome_Series", "VIP_Exclusive", "Flash_Sale_Alert",
        "Electronics_Weekend_Deal", "Book_Recommendations",
    ],
    "affiliate": [
        "Cashback_Partners", "Coupon_Sites", "Influencer_Tech",
        "Influencer_Fashion", "Comparison_Sites",
        "Home_Living_Bloggers", "Book_Review_Sites",
    ],
}

AFFINITY_GROUPS = [
    ["Mechanical Keyboard", "Gaming Mouse", "LED Monitor 27\"", "USB-C Hub"],
    ["Wireless Earbuds", "Portable Charger", "Bluetooth Adapter"],
    ["NC Headphones", "USB Microphone", "Ring Light Kit"],
    ["Smart Watch", "Fitness Tracker Band", "Compression Socks"],
    ["Webcam HD", "Laptop Cooling Pad", "HDMI Cable 6ft"],
    ["Smart Plug WiFi", "WiFi Extender", "Smart Doorbell"],
    ["External SSD 1TB", "Wireless Charger Pad", "Power Strip Surge"],
    ["Dash Cam 4K", "Action Camera", "Portable Projector"],
    ["VR Headset", "Drone Mini", "RC Drone Mini"],
    ["Yoga Mat Premium", "Resistance Band Set", "Foam Roller", "Jump Rope Speed"],
    ["Dumbbell Adjustable", "Pull-Up Bar Doorway", "Kettlebell Cast Iron", "Ab Roller Wheel"],
    ["Hiking Backpack 40L", "Camping Hammock", "Insulated Water Bottle"],
    ["Cricket Bat Kashmir", "Badminton Racket Pro", "Table Tennis Set"],
    ["Tennis Racket", "Soccer Ball Size 5", "Swim Goggles"],
    ["Boxing Gloves", "Ankle Weights 5lb", "Wrist Wraps"],
    ["Treadmill Foldable", "Gym Bag Duffel", "Protein Shaker"],
    ["Air Fryer 5qt", "Electric Kettle", "Kitchen Scale Digital"],
    ["French Press Coffee", "Coffee Grinder", "Vacuum Insulated Mug"],
    ["Stainless Steel Blender", "Immersion Blender", "Silicone Spatula Set"],
    ["Cast Iron Skillet", "Bamboo Cutting Board", "Nonstick Pan Set"],
    ["Instant Pot 6qt", "Pressure Cooker", "Rice Cooker"],
    ["Toaster Oven", "Hand Mixer", "Baking Sheet Set"],
    ["Ceramic Knife Set", "Mandoline Slicer", "Mortar Pestle Marble"],
    ["Vitamin C Serum", "Hyaluronic Acid Serum", "Sunscreen SPF 50"],
    ["Retinol Moisturizer", "Eye Cream Anti-Aging", "Facial Cleansing Brush"],
    ["Beard Grooming Kit", "Shaving Kit Premium", "Electric Toothbrush"],
    ["Charcoal Face Mask", "Jade Roller Set", "Dead Sea Salt Scrub"],
    ["Hair Growth Oil", "Hair Serum Argan", "Dry Shampoo"],
    ["Turmeric Face Cream", "Neem Face Wash", "Rose Water Toner"],
    ["Coconut Oil Cold-Pressed", "Aloe Vera Gel Organic", "Kumkumadi Tailam"],
    ["Automatic Pet Feeder", "Pet Water Fountain", "Pet Grooming Kit"],
    ["Dog Harness No-Pull", "Dog Leash Retractable", "Dog Training Treats", "Dog Raincoat"],
    ["Cat Tree Tower", "Cat Scratching Post", "Catnip Toy Set", "Cat Litter Mat"],
    ["Fish Tank Filter", "Aquarium LED Light", "Aquarium Plants Set"],
    ["Bird Cage Large", "Bird Seed Mix 2kg", "Parrot Perch Stand"],
    ["Atomic Habits", "Deep Work", "Essentialism", "Start with Why"],
    ["Clean Code", "The Pragmatic Programmer", "Designing Data-Intensive Apps"],
    ["The Lean Startup", "Zero to One", "Good to Great"],
    ["Sapiens", "Thinking Fast and Slow", "Influence Psychology"],
    ["Python Crash Course", "The Data Warehouse Toolkit", "The Phoenix Project"],
    ["Rich Dad Poor Dad", "Ikigai", "The Alchemist"],
    ["Classic Crew T-Shirt", "Slim Fit Jeans", "Leather Belt"],
    ["Yoga Leggings", "Sports Bra", "Running Shorts"],
    ["Bomber Jacket", "Puffer Vest", "Beanie Cap"],
    ["Kurta Set", "Silk Scarf", "Formal Shirt"],
    ["Wool Overcoat", "V-Neck Sweater", "Chino Pants"],
    ["Lightweight Hoodie", "Cargo Joggers", "Graphic Tee"],
    ["LEGO Architecture Set", "Puzzle 1000pc", "Chess Set Wooden"],
    ["RC Drone Mini", "Remote Control Car", "Nerf Blaster"],
    ["Science Kit Kids", "Coding Robot Kit", "Telescope Kids"],
    ["Board Game Strategy", "Card Game Party", "Magic Kit Beginner"],
]


def _hash(val: str) -> str:
    return hashlib.sha256(val.encode()).hexdigest()[:16]


def _seasonal_weight(dt: datetime) -> float:
    month = dt.month
    day = dt.day
    w = {1: 0.90, 2: 0.70, 3: 0.80, 4: 0.85, 5: 0.80, 6: 0.85,
         7: 0.95, 8: 1.00, 9: 0.95, 10: 1.20, 11: 1.50, 12: 1.40}.get(month, 1.0)
    if (month == 10 and day >= 20) or (month == 11 and day <= 5):
        w *= 1.6
    if month == 1 and 20 <= day <= 26:
        w *= 1.3
    if month == 8 and 10 <= day <= 16:
        w *= 1.3
    return w


def _build_product_catalog(rng: random.Random) -> tuple[list[dict], set[str], dict[str, list[dict]]]:
    products: list[dict] = []
    pid = 1
    for cat, items in CATEGORIES.items():
        for item_name, base_price in items:
            products.append({
                "product_id": f"PROD-{pid:04d}",
                "product_name": item_name,
                "category": cat,
                "base_price": base_price,
            })
            pid += 1

    inactive_ids = set(rng.sample([p["product_id"] for p in products], k=int(len(products) * 0.05)))

    name_to_prod = {p["product_name"]: p for p in products}
    affinity_map: dict[str, list[dict]] = {}
    for group in AFFINITY_GROUPS:
        group_prods = [name_to_prod[n] for n in group if n in name_to_prod]
        for p in group_prods:
            related = [r for r in group_prods if r["product_id"] != p["product_id"]]
            if p["product_id"] not in affinity_map:
                affinity_map[p["product_id"]] = related
            else:
                affinity_map[p["product_id"]].extend(related)

    return products, inactive_ids, affinity_map


def _build_customers(rng: random.Random) -> tuple[list[dict], list[float]]:
    customers: list[dict] = []
    weights: list[float] = []
    for i in range(NUM_CUSTOMERS):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        email = f"{first.lower()}.{last.lower()}{rng.randint(1, 9999)}@example.com"
        region = rng.choice(REGIONS)

        roll = rng.random()
        if roll < 0.15:
            weight = rng.uniform(3.0, 8.0)
        elif roll < 0.40:
            weight = rng.uniform(1.5, 3.0)
        elif roll < 0.75:
            weight = rng.uniform(0.5, 1.5)
        else:
            weight = rng.uniform(0.05, 0.3)

        customers.append({
            "customer_id": f"CUST-{i + 1:05d}",
            "email_hash": _hash(email),
            "name_hash": _hash(f"{first} {last}"),
            "region": region,
        })
        weights.append(weight)

    total_w = sum(weights)
    probs = [w / total_w for w in weights]
    return customers, probs


def _generate_orders(
    rng: random.Random,
    products: list[dict],
    inactive_ids: set[str],
    affinity_map: dict[str, list[dict]],
    customers: list[dict],
    customer_probs: list[float],
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    total_days = (end_date - start_date).days
    active_products = [p for p in products if p["product_id"] not in inactive_ids]

    rows: list[dict] = []
    order_num = 0
    i = 0

    while i < NUM_ORDERS:
        for _ in range(20):
            day_offset = rng.randint(0, total_days)
            dt = start_date + timedelta(days=day_offset)
            if rng.random() < _seasonal_weight(dt) / 3.0:
                break

        order_date = dt.replace(
            hour=rng.randint(6, 23),
            minute=rng.randint(0, 59),
            second=rng.randint(0, 59),
        )

        cust_idx = rng.choices(range(NUM_CUSTOMERS), weights=customer_probs, k=1)[0]
        cust = customers[cust_idx]

        lines_roll = rng.random()
        if lines_roll < 0.50:
            num_lines = 1
        elif lines_roll < 0.75:
            num_lines = 2
        elif lines_roll < 0.90:
            num_lines = 3
        else:
            num_lines = rng.randint(4, 7)
        num_lines = min(num_lines, NUM_ORDERS - i)

        order_num += 1
        order_id = f"ORD-{order_num:06d}"
        status = rng.choice(STATUSES_WEIGHTED)
        channel = rng.choice(CHANNELS)

        use_inactive = rng.random() < 0.02 and bool(inactive_ids)
        used_pids: set[str] = set()
        first_prod = None

        for line_idx in range(num_lines):
            if use_inactive:
                prod = rng.choice([p for p in products if p["product_id"] in inactive_ids])
            elif line_idx == 0:
                prod = rng.choice(active_products)
                first_prod = prod
            elif (first_prod and first_prod["product_id"] in affinity_map
                  and rng.random() < 0.80):
                related = [r for r in affinity_map[first_prod["product_id"]]
                           if r["product_id"] not in used_pids
                           and r["product_id"] not in inactive_ids]
                prod = rng.choice(related) if related else rng.choice(active_products)
            else:
                prod = rng.choice(active_products)

            attempts = 0
            while prod["product_id"] in used_pids and attempts < 10:
                prod = rng.choice(active_products)
                attempts += 1
            used_pids.add(prod["product_id"])

            qty_roll = rng.random()
            if qty_roll < 0.50:
                qty = 1
            elif qty_roll < 0.75:
                qty = 2
            elif qty_roll < 0.88:
                qty = 3
            elif qty_roll < 0.95:
                qty = rng.randint(4, 6)
            else:
                qty = rng.randint(7, 20)

            unit_price = round(prod["base_price"] * rng.uniform(0.85, 1.15), 2)
            total_price = round(unit_price * qty, 2)

            discount = 0.0
            if rng.random() < 0.25:
                discount_pct = rng.choice([0.05, 0.10, 0.10, 0.15, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50])
                discount = round(total_price * discount_pct, 2)

            refund = 0.0
            refund_reason = ""
            if status == "refunded":
                refund_pct = rng.choice([0.5, 0.75, 1.0, 1.0, 1.0])
                refund = round((total_price - discount) * refund_pct, 2)
                refund_reason = rng.choice(REFUND_REASONS)

            rows.append({
                "order_id": order_id,
                "order_date": order_date.strftime("%Y-%m-%d %H:%M:%S"),
                "customer_id": cust["customer_id"],
                "customer_email_hash": cust["email_hash"],
                "customer_name_hash": cust["name_hash"],
                "product_id": prod["product_id"],
                "product_name": prod["product_name"],
                "category": prod["category"],
                "quantity": qty,
                "unit_price": unit_price,
                "total_price": total_price,
                "discount_amount": discount,
                "currency": "INR",
                "status": status,
                "refund_amount": refund,
                "refund_reason": refund_reason,
                "channel": channel,
                "region": cust["region"],
                "line_item_index": line_idx,
            })
            i += 1

    logger.info("Generated %d order rows", len(rows))
    return pd.DataFrame(rows)


def _generate_products(
    rng: random.Random,
    products: list[dict],
    inactive_ids: set[str],
) -> pd.DataFrame:
    colors = ["Red", "Blue", "Black", "White", "Green", "Grey", "Navy", "Beige", "Brown", ""]
    sizes = ["S", "M", "L", "XL", "One Size", ""]

    rows: list[dict] = []
    for p in products:
        is_inactive = p["product_id"] in inactive_ids
        cost = round(p["base_price"] * rng.uniform(0.35, 0.55), 2)
        stock = 0 if is_inactive else rng.randint(0, 800)
        if not is_inactive and rng.random() < 0.08:
            stock = 0

        rows.append({
            "product_id": p["product_id"],
            "product_name": p["product_name"],
            "category": p["category"],
            "subcategory": "",
            "unit_cost": cost,
            "current_stock": stock,
            "status": "inactive" if is_inactive else "active",
            "size": rng.choice(sizes) if p["category"] == "Clothing" else "",
            "color": rng.choice(colors) if p["category"] in ("Clothing", "Electronics") else "",
        })

    logger.info("Generated %d products", len(rows))
    return pd.DataFrame(rows)


def _generate_customers(
    rng: random.Random,
    customers: list[dict],
    orders_df: pd.DataFrame,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    total_days = (end_date - start_date).days

    cust_stats: dict[str, dict] = {}
    for _, row in orders_df.iterrows():
        cid = row["customer_id"]
        if row["status"] == "cancelled":
            continue
        net = float(row["total_price"]) - float(row["discount_amount"])
        if cid not in cust_stats:
            cust_stats[cid] = {
                "order_ids": set(),
                "first_date": row["order_date"],
                "last_date": row["order_date"],
                "total_spend": 0.0,
            }
        cust_stats[cid]["order_ids"].add(row["order_id"])
        cust_stats[cid]["total_spend"] += net
        if row["order_date"] < cust_stats[cid]["first_date"]:
            cust_stats[cid]["first_date"] = row["order_date"]
        if row["order_date"] > cust_stats[cid]["last_date"]:
            cust_stats[cid]["last_date"] = row["order_date"]

    rows: list[dict] = []
    for c in customers:
        cid = c["customer_id"]
        stats = cust_stats.get(cid)
        if stats:
            total_orders = len(stats["order_ids"])
            total_spend = round(stats["total_spend"], 2)
            avg_val = round(total_spend / total_orders, 2) if total_orders else 0
            rows.append({
                "customer_id": cid,
                "email_hash": c["email_hash"],
                "name_hash": c["name_hash"],
                "first_order_date": stats["first_date"],
                "last_order_date": stats["last_date"],
                "total_orders": total_orders,
                "total_spend": total_spend,
                "avg_order_value": avg_val,
                "region": c["region"],
            })
        else:
            reg_date = (start_date + timedelta(days=rng.randint(0, total_days))).strftime("%Y-%m-%d")
            rows.append({
                "customer_id": cid,
                "email_hash": c["email_hash"],
                "name_hash": c["name_hash"],
                "first_order_date": reg_date,
                "last_order_date": reg_date,
                "total_orders": 0,
                "total_spend": 0.00,
                "avg_order_value": 0.00,
                "region": c["region"],
            })

    logger.info("Generated %d customers", len(rows))
    return pd.DataFrame(rows)


def _generate_reviews(
    rng: random.Random,
    orders_df: pd.DataFrame,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    total_days = (end_date - start_date).days

    product_buyers: dict[str, list[str]] = {}
    for _, row in orders_df.iterrows():
        pid = row["product_id"]
        cid = row["customer_id"]
        if pid not in product_buyers:
            product_buyers[pid] = []
        product_buyers[pid].append(cid)

    pids_with_buyers = list(product_buyers.keys())

    rows: list[dict] = []
    for rev_i in range(NUM_REVIEWS):
        pid = rng.choice(pids_with_buyers)
        cid = rng.choice(product_buyers[pid])

        rating_roll = rng.random()
        if rating_roll < 0.05:
            rating = 1
        elif rating_roll < 0.12:
            rating = 2
        elif rating_roll < 0.25:
            rating = 3
        elif rating_roll < 0.55:
            rating = 4
        else:
            rating = 5

        if rating >= 4:
            text = rng.choice(REVIEW_POSITIVE)
            sentiment_score = round(rng.uniform(0.65, 0.95), 3)
            sentiment_label = "positive"
        elif rating == 3:
            text = rng.choice(REVIEW_NEUTRAL)
            sentiment_score = round(rng.uniform(0.40, 0.60), 3)
            sentiment_label = "neutral"
        else:
            text = rng.choice(REVIEW_NEGATIVE)
            sentiment_score = round(rng.uniform(0.05, 0.35), 3)
            sentiment_label = "negative"

        if rng.random() < 0.3:
            text += rng.choice(REVIEW_EXTRAS)

        day_offset = rng.randint(0, total_days)
        review_date = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")

        rows.append({
            "review_id": f"REV-{rev_i + 1:05d}",
            "product_id": pid,
            "customer_id": cid,
            "review_date": review_date,
            "rating": rating,
            "review_text": text,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
        })

    logger.info("Generated %d reviews", len(rows))
    return pd.DataFrame(rows)


def _generate_ad_spend(
    rng: random.Random,
    start_date: datetime,
) -> pd.DataFrame:
    ad_channels = ["google_ads", "meta_ads", "tiktok", "email", "affiliate"]

    rows: list[dict] = []
    for day_off in range(AD_SPEND_DAYS):
        dt = start_date + timedelta(days=day_off)
        date_str = dt.strftime("%Y-%m-%d")
        seasonal = _seasonal_weight(dt)

        for ch in ad_channels:
            campaigns = CAMPAIGN_NAMES.get(ch, [f"{ch}_default"])
            active_campaigns = [c for c in campaigns if rng.random() < 0.7]
            if not active_campaigns:
                active_campaigns = [rng.choice(campaigns)]

            for camp in active_campaigns:
                base_spend = {
                    "google_ads": rng.uniform(2000, 8000),
                    "meta_ads": rng.uniform(1500, 6000),
                    "tiktok": rng.uniform(500, 3000),
                    "email": rng.uniform(100, 500),
                    "affiliate": rng.uniform(300, 2000),
                }.get(ch, 1000)

                spend = round(base_spend * seasonal * rng.uniform(0.6, 1.4) / len(active_campaigns), 2)
                cpm = rng.uniform(40, 200)
                impressions = max(100, int(spend / cpm * 1000))
                ctr = rng.uniform(0.005, 0.06)
                clicks = max(1, int(impressions * ctr))
                cvr = rng.uniform(0.01, 0.08)
                conversions = max(0, int(clicks * cvr))
                avg_order = rng.uniform(800, 4000)
                revenue = round(conversions * avg_order, 2)

                rows.append({
                    "date": date_str,
                    "channel": ch,
                    "campaign_name": camp,
                    "impressions": impressions,
                    "clicks": clicks,
                    "spend": spend,
                    "currency": "INR",
                    "conversions": conversions,
                    "revenue_attributed": revenue,
                })

    logger.info("Generated %d ad_spend rows", len(rows))
    return pd.DataFrame(rows)


def _generate_stock_levels(
    rng: random.Random,
    products: list[dict],
    inactive_ids: set[str],
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    active_products = [p for p in products if p["product_id"] not in inactive_ids]

    rows: list[dict] = []
    for p in active_products:
        base_stock = rng.randint(20, 500)
        lead_time = rng.choice([3, 5, 7, 7, 10, 14, 14, 21, 30])

        for week in range(STOCK_SNAPSHOT_WEEKS):
            snap_date = start_date + timedelta(weeks=week)
            if snap_date > end_date:
                break

            seasonal = _seasonal_weight(snap_date)
            demand = int(base_stock * 0.3 * seasonal * rng.uniform(0.5, 1.5))
            restock = int(base_stock * 0.25 * rng.uniform(0.3, 1.2))
            stock = max(0, base_stock - demand + restock)

            if rng.random() < 0.05:
                stock = 0
            if rng.random() < 0.03:
                stock = int(base_stock * rng.uniform(2.0, 4.0))

            base_stock = stock

            rows.append({
                "product_id": p["product_id"],
                "snapshot_date": snap_date.strftime("%Y-%m-%d"),
                "quantity_on_hand": stock,
                "lead_time_days": lead_time,
            })

    logger.info("Generated %d stock_levels rows", len(rows))
    return pd.DataFrame(rows)


def generate_sample_data() -> dict[str, pd.DataFrame]:
    """Generate the complete sample e-commerce dataset in memory.

    All dates are relative to today — no CSV files or external scripts needed.
    Works in both development and frozen (PyInstaller) mode.
    """
    rng = random.Random(SEED)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=AD_SPEND_DAYS)

    logger.info(
        "Generating sample data in memory: %s to %s (~18 months)",
        start_date.date(), end_date.date(),
    )

    products, inactive_ids, affinity_map = _build_product_catalog(rng)
    customers, customer_probs = _build_customers(rng)

    orders_df = _generate_orders(
        rng, products, inactive_ids, affinity_map,
        customers, customer_probs, start_date, end_date,
    )
    products_df = _generate_products(rng, products, inactive_ids)
    customers_df = _generate_customers(rng, customers, orders_df, start_date, end_date)
    reviews_df = _generate_reviews(rng, orders_df, start_date, end_date)
    ad_spend_df = _generate_ad_spend(rng, start_date)
    stock_levels_df = _generate_stock_levels(rng, products, inactive_ids, start_date, end_date)

    result = {
        "orders": orders_df,
        "customers": customers_df,
        "products": products_df,
        "reviews": reviews_df,
        "ad_spend": ad_spend_df,
        "stock_levels": stock_levels_df,
    }

    total_rows = sum(len(df) for df in result.values())
    logger.info("Sample data generation complete: %d total rows across %d tables", total_rows, len(result))

    return result
