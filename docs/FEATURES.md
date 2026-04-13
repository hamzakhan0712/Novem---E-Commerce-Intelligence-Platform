# Features

This document explains every feature in NOVEM — what it does, how it works under the hood, and why it matters for the user.

---

## 1. Data Import Pipeline

### What It Does
Lets users bring their e-commerce data into NOVEM from multiple sources: file uploads, Google Sheets, Shopify API, and PostgreSQL/MySQL databases.

### How It Works

**File Upload** (CSV, TSV, Excel):
1. User drags and drops a file onto the import page (or clicks to browse)
2. Engine parses the file, auto-detects the delimiter and encoding
3. Schema detector examines column names to identify the data type (orders? customers? products?)
4. Column mapper suggests how to map uploaded columns to NOVEM's canonical schema — using exact match, synonym matching (350+ platform-specific aliases), and Levenshtein fuzzy matching
5. User sees a 10-row preview and can adjust mappings
6. On confirm: data is cleaned, PII is masked, quality is scored, and data is merged into DuckDB

**Google Sheets**:
- User pastes a public Google Sheets URL
- Engine extracts the CSV export URL, downloads the data, and follows the same pipeline

**Shopify**:
- User provides API credentials (encrypted with Fernet)
- Engine calls the Shopify REST API with cursor-based pagination
- Rate limits enforced: 2 req/s
- Supports scheduled recurring syncs via APScheduler

**Database (PostgreSQL / MySQL)**:
- User provides connection credentials
- Engine connects read-only, lets user select tables and map them to data types
- Custom SQL queries supported with read-only enforcement

### Multi-File and Batch Import
- Upload multiple files at once — each gets its own schema detection
- Import multiple Google Sheets tabs from one spreadsheet
- Import multiple database tables in a single operation

### Quality Scoring
Every import gets an 8-point quality score (0-100), checking: null rate, duplicate rate, date validity, negative values, currency consistency, schema match, row count, and data freshness. Score tiers: Healthy (≥80), Needs Review (≥50), Poor (<50).

### PII Masking
By default, email and name columns are SHA-256 hashed before storage. Users can disable this in settings if they want to keep raw PII.

---

## 2. Performance Dashboard

### What It Does
Shows the big picture of the business at a glance — key metrics, trends over time, data quality, and revenue at risk.

### KPIs Calculated
| KPI | How It's Computed |
|---|---|
| Revenue | `SUM(total_price - discount_amount)` for the period |
| Orders | Count of distinct `order_id` values |
| Unique Customers | Count of distinct `customer_id` values |
| Average Order Value | Revenue ÷ Orders |
| Repeat Rate | % of customers with more than one order |
| New vs Returning | Ratio of first-time to repeat buyers |
| Refund Rate | Refund amount ÷ total revenue |
| Avg Items per Order | Avg line items per order |
| Revenue per Customer | Revenue ÷ unique customers |
| Churn Proxy | % of customers with no order in the last 90 days |

Each KPI includes a period-over-period comparison (e.g., "this 30 days vs previous 30 days") with percentage change.

### Revenue at Risk
Identifies customers who are overdue for a purchase based on their historical buying pattern. If a customer typically buys every 30 days but hasn't bought in 45 days, their expected spend is flagged as "at risk." This is displayed as a dollar clock on the dashboard.

### Trend Charts
Time-series charts for any metric at daily, weekly, or monthly granularity. Uses ECharts line charts with anomaly markers overlaid.

### Data Quality Card
Shows the overall data quality score with a breakdown of which quality checks are passing and failing.

---

## 3. Customer Intelligence

### Customer Analytics
- **Summary stats**: Total customers, returning rate, average lifetime value, total spend
- **Top customers**: Ranked by lifetime spend with order count and frequency
- **Segmentation**: Customers sorted into VIP, Regular, and Low-value tiers based on spend

### Churn Prediction
Uses the **BG/NBD model** from the `lifetimes` library. This is a probabilistic model that predicts the likelihood of a customer making another purchase within a given horizon (e.g., 30 days).

Inputs: frequency (how many repeat purchases), recency (when was the last purchase), T (how long since first purchase).

Output: churn probability (0-100%) for each customer, ordered by risk.

### Cohort Replay
A retention heatmap that groups customers by their first-purchase month and tracks what percentage return in months 1, 2, 3, etc. This shows how good the business is at keeping customers over time.

### Customer Stories
Generates a plain-language narrative about a specific customer's journey: when they first bought, how their spending has changed, what products they prefer, how they compare to the average.

### Customer Growth
Time-series showing new customers vs returning customers over the selected period.

---

## 4. Product Analytics

### Core Analytics
- **Summary**: Products sold, total units, product revenue, category count
- **Top products**: Ranked by revenue or units, with trend sparklines
- **Category breakdown**: Revenue and order count by product category

### Basket Analysis
Uses **mlxtend** for association rule mining. Finds which products are frequently bought together. Returns:
- **Support**: How often the combination appears
- **Confidence**: If a customer buys product A, how likely they are to also buy product B
- **Lift**: How much more likely the combination is compared to random chance

Configurable minimum support and confidence thresholds.

### Product Lifecycle Classification
BCG-inspired 4-quadrant classification based on revenue growth trend and volume:
- **Rising Star**: Growing revenue + growing volume → invest more
- **Cash Cow**: Stable high revenue → maintain and protect
- **Fading**: Declining revenue → consider discounting or bundling
- **Dead Weight**: Low and declining → consider discontinuing

### Inventory Intelligence
- **Reorder optimization**: Calculates Economic Order Quantity (EOQ), safety stock, and reorder points based on demand rate and lead times
- **Stock forecast**: Projects when each product will run out based on current stock and daily demand
- **Stockout impact**: Detects periods with zero stock and estimates revenue lost during those periods

---

## 5. Marketing Analytics

### What It Does
Analyzes ad spend data across all marketing channels to show which campaigns and channels actually generate ROI.

### KPIs
| KPI | Description |
|---|---|
| Total Spend | Sum of all ad spend in the period |
| ROAS | Return on Ad Spend (revenue ÷ spend) |
| CPC | Cost Per Click (spend ÷ clicks) |
| CTR | Click-Through Rate (clicks ÷ impressions) |
| Conversion Rate | Conversions ÷ clicks |
| CPA | Cost Per Acquisition (spend ÷ conversions) |

### Channel Breakdown
Per-channel performance showing which channels (Google, Meta, TikTok, email, etc.) are delivering the best results.

### Campaign Ranking
All campaigns ranked by the user's chosen metric (ROAS, spend, or conversions).

### Wasted Spend Detection
Cross-references ad spend with inventory data to find campaigns promoting products that are out of stock. Shows estimated money being wasted.

### Category ROI
Compares ad spend by product category against order revenue in that category to identify under/over-invested categories.

---

## 6. Insights Engine

The intelligence layer that generates automated insights across all data. This is where NOVEM's analytical brain lives.

### Auto-Generated Insights
15 insight rules (R001-R015) that analyze data and produce prioritized findings:
- High-LTV customers at high churn risk
- Customer segment imbalances
- Demand surge detection
- Complaint clusters from reviews
- 3σ revenue anomalies
- And 10 more rules

Each insight includes a confidence score based on data quality and sample size.

### Anomaly Detection
Uses IQR-based and Z-score methods to detect unusual patterns in KPIs. When daily revenue suddenly drops 40% or customer acquisition spikes unexpectedly, the system flags it.

Each anomaly includes:
- What happened (metric, direction, magnitude)
- When it was detected
- Time-to-detection (how quickly the system caught it)

### Causal Breakdown
When revenue changes, this feature decomposes the change into concrete causes:
- **Volume effect**: Did you sell more/fewer units?
- **Price effect**: Did prices change?
- **Interaction effect**: Combined volume × price impact
- **Refund impact**: Did refunds increase/decrease?
- **Channel mix shift**: Did the sales channel mix change?
- **Category mix shift**: Did the product category mix change?
- **New vs returning**: Did the customer type mix change?

### Missed Revenue Detection
Three categories of revenue the business could have captured but didn't:
- **Refund losses**: Revenue given back through refunds
- **Churn losses**: Expected spending from customers who stopped buying
- **Stockout signals**: Potential revenue lost during out-of-stock periods

### Business Health Score
A 0-100 composite score combining four dimensions:
- Revenue growth trend (35%)
- Customer health (25%)
- Operational efficiency (20%)
- Growth momentum (20%)

### Business DNA
A 6-dimension "fingerprint" of the business, visualized as a radar chart:
- Pricing power
- Customer loyalty
- Product diversity
- Marketing efficiency
- Operational health
- Growth trajectory

Also assigns an archetype: "Growth Engine", "Loyalty Leader", "Efficiency Expert", etc.

### Root Cause Narratives
Uses **Ollama** (if available) to generate human-readable explanations of why anomalies happened. Falls back to template-based narratives if Ollama is offline.

### SHAP Explanations
Uses **SHAP** (SHapley Additive exPlanations) to explain which features most strongly drive customer churn. Shows feature importance with direction (positive = increases churn, negative = decreases churn).

### Scenario Simulator
What-If analysis: user adjusts variables (e.g., "+10% marketing spend" or "-5% refund rate") and sees the projected impact on revenue and other KPIs.

### Explain This Metric
For any KPI, generates a plain-language explanation of what the metric means, why it's at its current level, and what factors are influencing it.

### Recommended Actions
6 data-driven actions sorted by estimated dollar impact:
1. Refund reduction opportunities
2. At-risk customer recovery campaigns
3. AOV increase through bundling
4. Promotional campaign opportunities
5. Channel expansion possibilities
6. Retention email campaigns

Each action includes an estimated `impact_dollars` value and a confidence score.

---

## 7. Forecasting

### What It Does
Predicts future values of key metrics (revenue, orders, customers) using time-series forecasting.

### How It Works
- Primary: **Facebook Prophet** — handles seasonality, trends, and holidays automatically
- Fallback: **Linear regression** — used when Prophet fails or data is too sparse
- Horizons: 30, 60, or 90 days ahead
- Returns: historical data, forecasted values, upper bound (95% CI), lower bound (95% CI)

### Metrics Overview
A quick-look endpoint that shows forecast highlights for all metrics at once — expected revenue next month, expected order count, etc.

---

## 8. Sentiment Analysis

### What It Does
Analyzes product reviews to understand customer satisfaction and identify problem areas.

### How It Works
- **Scoring**: TextBlob polarity scoring (-1.0 to +1.0)
- **Labels**: positive (>0.1), neutral (-0.1 to 0.1), negative (<-0.1)
- **Keywords**: Extracts top positive and negative words from review text
- **Per-product**: Aggregates sentiment at the product level to identify which products need attention

### Features
- **Sentiment KPIs**: Average rating, average sentiment score, review count with period comparison
- **Rating breakdown**: Distribution of 1-5 star ratings with sentiment scores per tier
- **Sentiment trend**: Daily average sentiment over time
- **Products needing attention**: Products with the lowest sentiment — candidates for quality improvement
- **Keyword cloud**: Visual representation of positive and negative themes

---

## 9. AI Copilot

### What It Does
A chat-based AI assistant that answers business questions using the store's actual data.

### How It Works
1. User types a question ("What was my best month for revenue?")
2. Engine builds **RAG context** by pulling relevant data from DuckDB: store overview, monthly revenue, customer metrics, top products, categories, refunds, reviews, channels
3. If Ollama is running: question + context is sent to the local LLM
4. If Ollama is offline: question is matched against 11 rule-based SQL templates (pattern matching)
5. Answer is returned with source attribution

### Model Management
- 5 supported models: llama3.2 (2.0 GB), phi3:mini (2.2 GB), qwen2.5:7b (4.7 GB), qwen2.5-coder:7b (4.7 GB), qwen2.5-coder:14b (9.0 GB)
- Users can install, switch, and delete models from the UI
- Model recommendations based on system specs

### RAG Context
The system prompt includes:
- Store name, platform, industry
- Currency and regional settings
- Monthly revenue and order trends
- Customer count and returning rate
- Top products and categories
- Refund rates and sentiment summary
- Active anomalies and health score

This means the LLM answers with knowledge of the user's actual business data, not generic responses.

### Guardrails
- Rate limiting: 30 messages per minute per session
- Max message length: 500 words
- Feedback collection: thumbs up/down on each answer
- Generic error messages to users, full exceptions logged server-side

---

## 10. Data Import via External Connectors

### Shopify Connector
- REST API integration with cursor-based pagination
- 2 requests/second rate limit
- Syncs: orders, customers, products, reviews, stock levels
- HMAC-SHA256 webhook verification for real-time data

### Google Sheets Connector
- Reads public spreadsheets by URL
- Also supports Google Sheets API v4 for authenticated access

### Database Connector
- PostgreSQL and MySQL support via psycopg2 and pymysql
- Structured mode: map tables to data types
- Custom SQL mode: user writes their own query
- Read-only enforcement: only SELECT/WITH/EXPLAIN/SHOW allowed

### Recurring Syncs
- APScheduler manages recurring sync jobs
- Configurable intervals (hourly, daily, weekly)
- Schedules persisted to SQLite, restored on engine restart
- Manual trigger available at any time

---

## 11. Export & Reports

### CSV Export
- Export any data table as a CSV file
- Preview row count before downloading
- Auto-cleanup of export files older than 1 hour

### Narrative Reports
AI-generated business intelligence reports with:
- KPI highlights
- Trend analysis
- Anomaly summary
- Recommended actions

### PDF Generation
Full business reports generated as PDF using ReportLab. Includes charts, tables, and narrative text.

---

## 12. Alerts & Notifications

### Threshold Alerts
Set thresholds on KPIs (e.g., "alert me if daily revenue drops below $500"). The engine checks thresholds and creates alerts automatically.

### Alert Management
- Severity levels: info, warning, critical
- Mark as read, mark all as read, delete
- Notification badge in the title bar
- Alert panel popover with severity-colored cards

### Email Digests
- Configure SMTP settings
- Send anomaly digest emails
- Track email send history

---

## 13. Data Viewer

A built-in data browser for inspecting raw analytical data:
- Browse any DuckDB table with pagination
- Sort by any column
- Full-text search across rows
- Column metadata and quick stats
- Delete data per table or per store

---

## 14. Store Management

### Multi-Store Support
Users can create multiple stores and switch between them. Each store:
- Has its own data, settings, and credentials
- Can be connected to a different platform (Shopify, etc.)
- Can be deactivated (soft delete) and reactivated
- Can be permanently deleted (cascades to all data)

### Store Switcher
A grid view showing all stores with platform badges, data counts, and one-click switching.

---

## 15. Settings & Personalization

7 settings sections:

| Section | What It Controls |
|---|---|
| **Profile** | Name, email |
| **Stores** | Store list, add/edit/switch stores |
| **Appearance** | Theme (dark/light), zoom level |
| **Regional** | Currency, date format, fiscal year start |
| **Security** | Change password, password policy, PII masking |
| **Email** | SMTP configuration for email alerts |
| **System** | Storage usage, file paths, cache management, version info |

### Currency Conversion
- Live exchange rates from ECB (via frankfurter.app)
- 24 currencies supported
- 1-hour cache with fallback static rates
- All amounts in the UI auto-convert to the user's selected currency

---

## 16. Auth & Security

### Authentication Flow
1. **First run**: User creates profile with name, email, password, and security Q&A
2. **Login**: Password verified with bcrypt, session token created
3. **Password policies**: "never" (no lock), "on startup" (login each launch), "monthly"
4. **Forgot password**: Verify security answer → get reset token → set new password
5. **Auto-lock**: Idle timer locks the app after inactivity (configurable)

### Security Features
- Passwords hashed with bcrypt (min 8 characters)
- Session tokens: `secrets.token_urlsafe(32)` with 24-hour TTL
- Login rate limiting: 5 attempts per 15-minute window
- PII masking: SHA-256 hashing on import
- Credential encryption: Fernet symmetric encryption
- SQL injection prevention: parameterized queries everywhere
- CORS restricted to localhost only
- No eval/exec anywhere in the codebase
