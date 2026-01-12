# AI Competitor Watchdog V1 - System Architecture

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CONFIGURATION LAYER                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  competitor_config.yaml  │  crawl_schedule.yaml          │  │
│  │  - Competitor URLs        │  - Frequency per asset type   │  │
│  │  - Asset type mappings    │  - Priority thresholds       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        CRAWLER LAYER                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Web Crawler                                              │  │
│  │  - Respects robots.txt                                    │  │
│  │  - Rate limiting (polite crawling)                        │  │
│  │  - Content extraction (HTML → clean text)                 │  │
│  │  - Sitemap parser (for new URL detection)                 │  │
│  │  - Change detection trigger                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        STORAGE LAYER                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Content Store (SQLite/PostgreSQL)                        │  │
│  │  - Snapshot history (URL, content_hash, timestamp)        │  │
│  │  - Change events (before/after, diff metadata)            │  │
│  │  - Asset metadata (competitor, asset_type, priority)      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DIFF ENGINE LAYER                        │
│  ┌──────────────────────────────────────────────────────────┘  │
│  │  Change Detection                                         │  │
│  │  - Semantic diff (ignore minor copy edits)               │  │
│  │  - Structural diff (HTML structure changes)               │  │
│  │  - Content extraction (pricing tables, feature lists)    │  │
│  │  - Noise filtering (ads, dynamic content)                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        CLASSIFIER LAYER                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  AI Classifier (LLM-based)                                │  │
│  │  - Change type detection                                  │  │
│  │  - Priority assignment (High/Medium/Low)                 │  │
│  │  - Insight generation (summary + "why it matters")        │  │
│  │  - Quality gate (reject low-signal changes)               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ALERTING LAYER                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Alert Manager                                            │  │
│  │  - Priority-based routing                                 │  │
│  │  - Delivery scheduling (real-time vs digest)              │  │
│  │  - Slack integration (webhook)                            │  │
│  │  - Message formatting (fixed schema)                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                        │
│  ┌──────────────────┐              ┌──────────────────┐        │
│  │  Slack Webhook   │              │  LLM API         │        │
│  │  (Alerts)        │              │  (OpenAI/Anthropic)       │
│  └──────────────────┘              └──────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Component Breakdown

### 2.1 Crawler Component
**Purpose**: Fetch and extract content from competitor web assets

**Responsibilities**:
- Scheduled crawling based on asset type and priority
- HTML parsing and content extraction
- Sitemap parsing for new URL detection
- Content normalization (remove ads, dynamic elements)
- Store raw snapshots for comparison

**Key Features**:
- Respects robots.txt and rate limits
- Handles JavaScript-rendered content (via headless browser if needed)
- Extracts structured data (pricing tables, feature lists)
- Tracks crawl metadata (timestamp, HTTP status, content hash)

### 2.2 Diff Engine Component
**Purpose**: Detect meaningful changes between content snapshots

**Responsibilities**:
- Compare current snapshot with previous version
- Semantic diff (understand context, not just text)
- Filter noise (minor copy edits, dynamic content, ads)
- Extract structured changes (pricing tiers, feature additions)
- Generate before/after summaries

**Change Detection Strategy**:
1. **Content Hash Comparison**: Fast filter for unchanged pages
2. **Text Diff**: Line-by-line comparison for structured content
3. **Semantic Diff**: Use LLM to identify meaningful changes
4. **Structured Extraction**: Parse pricing tables, feature lists, changelog entries
5. **Threshold Filtering**: Ignore changes below significance threshold

### 2.3 Classifier Component
**Purpose**: Analyze changes and generate competitive intelligence insights

**Responsibilities**:
- Classify change type (pricing, feature, compliance, etc.)
- Assign priority (High/Medium/Low) based on rules
- Generate concise summary (≤3 sentences)
- Explain "why it matters" (non-speculative)
- Quality gate (reject low-signal changes)

**AI Classification Approach**:
- Use LLM (GPT-4/Claude) for semantic understanding
- Provide structured prompt with:
  - Before/after content
  - Asset type context
  - Priority rules
  - Output schema
- Validate output against quality criteria

### 2.4 Alert Manager Component
**Purpose**: Route and deliver alerts based on priority and schedule

**Responsibilities**:
- Priority-based routing (High → immediate, Medium → daily, Low → weekly)
- Digest aggregation (batch low/medium priority alerts)
- Slack message formatting (fixed schema)
- Delivery scheduling
- Alert deduplication (prevent duplicate alerts for same change)

**Delivery Rules**:
- **High Priority**: Send immediately (< 5 minutes after detection)
- **Medium Priority**: Daily digest (9 AM daily)
- **Low Priority**: Weekly summary (Monday 9 AM)

## 3. Data Models / Schemas

### 3.1 Competitor Configuration
```yaml
competitors:
  - name: "DocuSign"
    base_url: "https://www.docusign.com"
    assets:
      - type: "pricing"
        url: "https://www.docusign.com/pricing"
        crawl_frequency: "daily"
        priority_threshold: "medium"
      - type: "features"
        url: "https://www.docusign.com/features"
        crawl_frequency: "weekly"
      - type: "changelog"
        url: "https://www.docusign.com/whats-new"
        crawl_frequency: "daily"
      - type: "sitemap"
        url: "https://www.docusign.com/sitemap.xml"
        crawl_frequency: "daily"
      - type: "news"
        url: "https://www.docusign.com/news"
        crawl_frequency: "daily"
      - type: "blog"
        url: "https://www.docusign.com/blog"
        crawl_frequency: "weekly"
        filters:
          - "product"
          - "pricing"
          - "AI"
          - "compliance"
      - type: "compliance"
        url: "https://www.docusign.com/trust/compliance"
        crawl_frequency: "weekly"
```

### 3.2 Database Schema

#### Table: `competitors`
```sql
CREATE TABLE competitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Table: `assets`
```sql
CREATE TABLE assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_id INTEGER NOT NULL,
    asset_type TEXT NOT NULL,  -- pricing, features, changelog, etc.
    url TEXT NOT NULL,
    crawl_frequency TEXT NOT NULL,  -- daily, weekly
    priority_threshold TEXT,  -- high, medium, low
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (competitor_id) REFERENCES competitors(id),
    UNIQUE(competitor_id, url)
);
```

#### Table: `snapshots`
```sql
CREATE TABLE snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    content_text TEXT,  -- extracted clean text
    content_html TEXT,  -- raw HTML (optional, for debugging)
    metadata JSON,  -- structured data (pricing tiers, features, etc.)
    crawl_timestamp TIMESTAMP NOT NULL,
    http_status INTEGER,
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    INDEX idx_asset_timestamp (asset_id, crawl_timestamp),
    INDEX idx_content_hash (content_hash)
);
```

#### Table: `changes`
```sql
CREATE TABLE changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    snapshot_before_id INTEGER NOT NULL,
    snapshot_after_id INTEGER NOT NULL,
    change_type TEXT,  -- pricing, feature, compliance, etc.
    priority TEXT,  -- high, medium, low
    summary TEXT,  -- ≤3 sentences
    why_it_matters TEXT,
    before_content TEXT,
    after_content TEXT,
    diff_metadata JSON,  -- structured diff data
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_sent BOOLEAN DEFAULT FALSE,
    alert_sent_at TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    FOREIGN KEY (snapshot_before_id) REFERENCES snapshots(id),
    FOREIGN KEY (snapshot_after_id) REFERENCES snapshots(id)
);
```

#### Table: `alerts`
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    change_id INTEGER NOT NULL,
    priority TEXT NOT NULL,
    slack_message_id TEXT,  -- for tracking
    sent_at TIMESTAMP,
    delivery_type TEXT,  -- immediate, daily_digest, weekly_summary
    FOREIGN KEY (change_id) REFERENCES changes(id)
);
```

## 4. Crawl + Diff Strategy

### 4.1 Crawl Strategy

**Frequency by Asset Type**:
- **Pricing pages**: Daily (high signal, frequent changes)
- **Feature/Solution pages**: Weekly (less frequent changes)
- **Changelog pages**: Daily (time-sensitive)
- **Sitemaps**: Daily (new URL detection)
- **News/Press**: Daily (time-sensitive)
- **Blogs**: Weekly (filtered by topic)
- **Compliance pages**: Weekly (infrequent but important)

**Crawl Process**:
1. Load competitor configuration
2. For each asset:
   - Check last crawl timestamp vs. frequency
   - Fetch URL (respect rate limits)
   - Extract content (HTML → clean text + structured data)
   - Compute content hash
   - Compare with last snapshot
   - If hash differs → trigger diff engine
   - Store snapshot

**Content Extraction**:
- **Pricing pages**: Extract pricing tiers, feature inclusions, free tier info
- **Feature pages**: Extract feature lists, capabilities
- **Changelog pages**: Extract entries with dates
- **Sitemaps**: Extract new URLs (compare with known URLs)
- **Blogs**: Extract title, date, tags (filter by topic)
- **Compliance pages**: Extract certifications, compliance standards

### 4.2 Diff Strategy

**Multi-Stage Diff Process**:

1. **Hash Comparison** (Fast Filter)
   - If content_hash matches previous snapshot → no change
   - Skip expensive diff processing

2. **Text Diff** (Structural)
   - Use diff algorithm (e.g., difflib) for line-by-line comparison
   - Identify added/removed/modified sections
   - Filter out noise (whitespace, formatting)

3. **Semantic Diff** (AI-Powered)
   - For structured content (pricing, features):
     - Extract structured data (JSON)
     - Compare structured representations
   - For unstructured content:
     - Use LLM to identify meaningful changes
     - Prompt: "Compare these two versions and identify significant changes"

4. **Change Significance Filter**
   - Ignore if:
     - Only formatting/styling changes
     - Minor copy edits (< 5% content change)
     - Dynamic content (ads, timestamps, counters)
   - Flag as significant if:
     - Pricing tier changes
     - Feature additions/removals
     - New compliance certifications
     - New URLs in sitemap

5. **Before/After Extraction**
   - Extract relevant sections (not full page)
   - Format for LLM classification
   - Include context (asset type, competitor)

## 5. Slack Integration Approach

### 5.1 Webhook Setup
- Use Slack Incoming Webhooks (simple, no OAuth needed)
- Configure webhook URL in environment variable
- Support multiple channels (optional: #competitive-intel-high, #competitive-intel-all)

### 5.2 Message Format (Fixed Schema)

```json
{
  "text": "Competitive Intelligence Alert",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "🔔 Competitor Change Detected"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn",
          "text": "*Company:*\n{competitor_name}"
        },
        {
          "type": "mrkdwn",
          "text": "*Priority:*\n{priority}"
        },
        {
          "type": "mrkdwn",
          "text": "*Asset:*\n{asset_type}"
        },
        {
          "type": "mrkdwn",
          "text": "*Change Type:*\n{change_type}"
        }
      ]
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Summary (Before → After):*\n{summary}"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Why It Matters:*\n{why_it_matters}"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Citation:*\n<{url}|{url}> (Detected: {timestamp})"
      }
    }
  ]
}
```

### 5.3 Delivery Scheduling

**Immediate Delivery (High Priority)**:
- Send within 5 minutes of detection
- Individual message per change

**Daily Digest (Medium Priority)**:
- Aggregate all medium-priority changes from last 24 hours
- Send at 9 AM daily
- Format as single message with sections for each change

**Weekly Summary (Low Priority)**:
- Aggregate all low-priority changes from last 7 days
- Send Monday 9 AM
- Format as digest with grouped by competitor

## 6. Initial Tech Stack Recommendation

### 6.1 Core Stack
- **Language**: Python 3.11+
  - Mature ecosystem for web scraping
  - Excellent LLM integration libraries
  - Simple deployment options

- **Web Scraping**:
  - `requests` + `BeautifulSoup4` (simple HTML parsing)
  - `selenium` or `playwright` (for JavaScript-rendered content, if needed)
  - `robots.txt` parser: `urllib.robotparser`

- **Content Diff**:
  - `difflib` (built-in text diff)
  - Custom semantic diff using LLM

- **Database**:
  - **V1**: SQLite (simple, no setup)
  - **Future**: PostgreSQL (if scale requires)

- **LLM Integration**:
  - `openai` library (GPT-4)
  - Alternative: `anthropic` (Claude)
  - Structured output via function calling or JSON mode

- **Scheduling**:
  - `schedule` library (simple cron-like scheduling)
  - Alternative: `APScheduler` (more features)

- **Slack Integration**:
  - `slack-sdk` or `requests` (webhook)

### 6.2 Project Structure
```
ai-competitor-watchdog/
├── config/
│   ├── competitors.yaml
│   └── crawl_schedule.yaml
├── src/
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── web_crawler.py
│   │   ├── content_extractor.py
│   │   └── sitemap_parser.py
│   ├── diff/
│   │   ├── __init__.py
│   │   ├── diff_engine.py
│   │   └── semantic_diff.py
│   ├── classifier/
│   │   ├── __init__.py
│   │   ├── change_classifier.py
│   │   └── priority_assigner.py
│   ├── alerting/
│   │   ├── __init__.py
│   │   ├── alert_manager.py
│   │   └── slack_integration.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── models.py
│   └── main.py
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

### 6.3 Environment Variables
```bash
# LLM API
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///watchdog.db
```

## 7. V1 Build Sequence (Step-by-Step)

### Phase 1: Foundation (Days 1-2)
1. **Project Setup**
   - Initialize Python project structure
   - Set up virtual environment
   - Create requirements.txt with core dependencies
   - Set up configuration file structure (YAML)

2. **Database Schema**
   - Create SQLite database
   - Implement database models/schema
   - Create database initialization script
   - Add basic CRUD operations

3. **Configuration System**
   - Create competitor configuration YAML parser
   - Create crawl schedule configuration
   - Add configuration validation

### Phase 2: Crawler (Days 3-4)
4. **Basic Web Crawler**
   - Implement HTTP fetching with rate limiting
   - Add robots.txt respect
   - Implement content extraction (HTML → text)
   - Add content normalization (remove ads, dynamic content)

5. **Content Extractors**
   - Implement asset-type-specific extractors:
     - Pricing page extractor (tables, tiers)
     - Feature page extractor (lists, capabilities)
     - Changelog extractor (entries with dates)
     - Sitemap parser (new URL detection)
     - Blog extractor (filtered by topic)
   - Store structured metadata in snapshots

6. **Scheduler**
   - Implement crawl scheduler based on frequency
   - Add last-crawl timestamp tracking
   - Test crawl execution

### Phase 3: Diff Engine (Days 5-6)
7. **Basic Diff**
   - Implement hash comparison
   - Add text diff (difflib)
   - Create change detection trigger

8. **Semantic Diff**
   - Implement LLM-based semantic diff
   - Add structured data comparison (pricing, features)
   - Filter noise (minor edits, dynamic content)
   - Generate before/after summaries

9. **Change Storage**
   - Store detected changes in database
   - Link changes to snapshots
   - Add change metadata

### Phase 4: Classifier (Days 7-8)
10. **Change Classification**
    - Implement LLM-based change type detection
    - Add priority assignment (High/Medium/Low) based on rules
    - Generate summary (≤3 sentences)
    - Generate "why it matters" explanation

11. **Quality Gate**
    - Implement quality filtering (reject low-signal changes)
    - Validate output format
    - Add error handling for LLM failures

### Phase 5: Alerting (Days 9-10)
12. **Slack Integration**
    - Set up Slack webhook
    - Implement message formatter (fixed schema)
    - Test message delivery

13. **Alert Manager**
    - Implement priority-based routing
    - Add immediate delivery for high priority
    - Implement daily digest for medium priority
    - Implement weekly summary for low priority
    - Add alert deduplication

### Phase 6: Integration & Testing (Days 11-12)
14. **End-to-End Integration**
    - Connect all components
    - Test full pipeline (crawl → diff → classify → alert)
    - Add error handling and logging

15. **Testing & Validation**
    - Test with real competitor URLs
    - Validate alert quality (signal vs. noise)
    - Tune LLM prompts for better accuracy
    - Add monitoring/logging

16. **Documentation**
    - Update README with setup instructions
    - Document configuration format
    - Add troubleshooting guide

### Phase 7: Deployment (Day 13)
17. **Deployment Setup**
    - Set up environment variables
    - Create deployment script
    - Test in production-like environment
    - Set up monitoring (basic logging)

## 8. Key Design Decisions

### 8.1 Why SQLite for V1?
- Zero setup, works out of the box
- Sufficient for small-scale monitoring (10-20 competitors)
- Easy migration to PostgreSQL later if needed

### 8.2 Why LLM for Classification?
- Semantic understanding needed (not just keyword matching)
- Flexible for different asset types
- Can be fine-tuned later if needed
- Cost-effective for low-volume V1

### 8.3 Why YAML Configuration?
- Human-readable, easy to edit
- No code changes needed to add competitors
- Version control friendly

### 8.4 Why Python?
- Rapid development
- Excellent libraries for scraping, LLM integration
- Simple deployment options
- Good for solo/small team

## 9. Success Metrics (V1)

- **Accuracy**: >90% of alerts are meaningful (not noise)
- **Coverage**: Monitor all defined asset types for configured competitors
- **Latency**: High-priority alerts within 5 minutes
- **Reliability**: 99%+ crawl success rate
- **Signal Quality**: <10% false positives (changes that aren't meaningful)

## 10. Future Considerations (Post-V1)

- Migration to PostgreSQL for scale
- Add webhook endpoints for external integrations
- Dashboard UI (out of scope for V1)
- Advanced filtering and search
- Historical trend analysis
- Multi-channel alerting (email, etc.)

