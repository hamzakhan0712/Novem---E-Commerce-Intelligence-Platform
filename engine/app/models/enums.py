from enum import Enum


# ── Time & Periods ──────────────────────────────────


class Period(str, Enum):
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"
    TWELVE_MONTHS = "12m"
    ALL = "all"


# ── Severity ────────────────────────────────────────


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ── Order & Status ──────────────────────────────────


class OrderStatus(str, Enum):
    COMPLETED = "completed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"
    PENDING = "pending"


# ── Data Ingestion ──────────────────────────────────


class DataType(str, Enum):
    ORDERS = "orders"
    CUSTOMERS = "customers"
    PRODUCTS = "products"
    AD_SPEND = "ad_spend"
    REVIEWS = "reviews"
    STOCK_LEVELS = "stock_levels"


class SourceType(str, Enum):
    FILE = "file"
    GOOGLE_SHEETS = "google_sheets"
    SAMPLE = "sample"
    SHOPIFY_API = "shopify_api"
    GOOGLE_SHEETS_API = "google_sheets_api"
    WEBHOOK = "webhook"
    POSTGRESQL = "postgresql"


class IndustryTemplate(str, Enum):
    GENERAL = "general"
    FASHION = "fashion"
    ELECTRONICS = "electronics"
    HOME_GARDEN = "home_garden"
    BEAUTY = "beauty"
    FOOD = "food"
    HEALTH = "health"
    SPORTS = "sports"
    TOYS = "toys"
    AUTOMOTIVE = "automotive"


# ── Store Management ────────────────────────────────


class StorePlatform(str, Enum):
    SHOPIFY = "shopify"
    CUSTOM = "custom"
    OTHER = "other"


class ImportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MergeStrategy(str, Enum):
    UPSERT = "upsert"
    APPEND = "append"
    REPLACE = "replace"


# ── Health & Quality ────────────────────────────────


class HealthTier(str, Enum):
    HEALTHY = "healthy"
    NEEDS_REVIEW = "needs_review"
    POOR = "poor"


# ── Customer Intelligence ───────────────────────────


class SegmentLabel(str, Enum):
    CHAMPIONS = "champions"
    LOYAL = "loyal"
    PROMISING = "promising"
    AT_RISK = "at_risk"
    NEEDS_ATTENTION = "needs_attention"
    LOST = "lost"


# ── Product Intelligence ───────────────────────────


class AbcClass(str, Enum):
    A = "A"
    B = "B"
    C = "C"


# ── Forecasting / Inventory ─────────────────────────


class InventoryStatus(str, Enum):
    HEALTHY = "healthy"
    REORDER_SOON = "reorder_soon"
    STOCKOUT_RISK = "stockout_risk"
    DEAD_STOCK = "dead_stock"


# ── Export ──────────────────────────────────────────


class ExportFormat(str, Enum):
    CSV = "csv"
    PDF = "pdf"


# ── Theme ───────────────────────────────────────────


class Theme(str, Enum):
    LIGHT = "light"
    DARK = "dark"
