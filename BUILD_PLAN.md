# AI Competitor Watchdog V1 - Build Plan

## Overview
This document provides a detailed, step-by-step build plan for V1 of the AI Competitor Watchdog system. Follow this sequence to build the system incrementally and test each component.

## Prerequisites
- Python 3.11 or higher
- API keys: OpenAI (or Anthropic) and Slack webhook URL
- Basic understanding of Python, web scraping, and LLM APIs

## Build Sequence

### Phase 1: Foundation (Days 1-2)

#### Step 1.1: Project Setup
**Goal**: Create project structure and dependencies

**Tasks**:
1. Create project directory structure
2. Initialize virtual environment
3. Create `requirements.txt` with initial dependencies:
   - `requests` (HTTP client)
   - `beautifulsoup4` (HTML parsing)
   - `pyyaml` (configuration)
   - `openai` or `anthropic` (LLM)
   - `slack-sdk` or `requests` (Slack webhook)
   - `schedule` (cron-like scheduling)
   - `sqlalchemy` (database ORM, optional) or direct SQLite
4. Create `.env.example` with required variables
5. Create basic `README.md` with setup instructions

**Deliverable**: Project structure ready, dependencies installable

---

#### Step 1.2: Database Schema
**Goal**: Set up data persistence layer

**Tasks**:
1. Create SQLite database file
2. Implement database schema (see ARCHITECTURE.md):
   - `competitors` table
   - `assets` table
   - `snapshots` table
   - `changes` table
   - `alerts` table
3. Create database initialization script
4. Add basic database connection/query utilities
5. Test schema creation and basic CRUD operations

**Deliverable**: Database schema created and tested

---

#### Step 1.3: Configuration System
**Goal**: Load and validate competitor configurations

**Tasks**:
1. Create `config/competitors.yaml` template
2. Create `config/crawl_schedule.yaml` template
3. Implement YAML configuration loader
4. Add configuration validation:
   - Required fields check
   - URL format validation
   - Asset type validation
   - Frequency validation
5. Create configuration helper functions

**Deliverable**: Configuration system loads and validates YAML files

**Test**: Load sample competitor config and validate structure

---

### Phase 2: Crawler (Days 3-4)

#### Step 2.1: Basic Web Crawler
**Goal**: Fetch and extract content from URLs

**Tasks**:
1. Implement HTTP fetcher with:
   - Rate limiting (respectful crawling)
   - User-agent header
   - Error handling (timeouts, 404s, etc.)
   - Retry logic
2. Implement robots.txt parser and respect
3. Create HTML parser (BeautifulSoup):
   - Extract clean text (remove scripts, styles)
   - Preserve structure where needed
4. Implement content normalization:
   - Remove ads, dynamic content
   - Normalize whitespace
   - Extract main content (skip headers/footers)
5. Compute content hash (SHA256 of normalized text)

**Deliverable**: Can fetch URLs and extract clean text

**Test**: Fetch a sample competitor URL and verify clean text extraction

---

#### Step 2.2: Content Extractors
**Goal**: Extract structured data by asset type

**Tasks**:
1. Create base `ContentExtractor` class
2. Implement asset-type-specific extractors:
   - **PricingExtractor**: Extract pricing tiers, feature inclusions, free tier info
     - Look for pricing tables, plan names, prices
     - Extract feature lists per tier
   - **FeatureExtractor**: Extract feature lists, capabilities
     - Parse feature lists, bullet points
   - **ChangelogExtractor**: Extract changelog entries with dates
     - Parse date + entry pairs
   - **SitemapExtractor**: Parse XML sitemap, extract URLs
     - Compare with known URLs to find new ones
   - **BlogExtractor**: Extract blog posts (filtered by topic)
     - Extract title, date, tags
     - Filter by keywords (product, pricing, AI, compliance)
   - **ComplianceExtractor**: Extract certifications, compliance standards
3. Store structured metadata (JSON) in snapshots table
4. Handle edge cases (missing elements, malformed HTML)

**Deliverable**: Can extract structured data for each asset type

**Test**: Test each extractor with real competitor pages

---

#### Step 2.3: Scheduler
**Goal**: Schedule crawls based on frequency

**Tasks**:
1. Implement crawl scheduler:
   - Load competitor configuration
   - Check last crawl timestamp for each asset
   - Determine if crawl is due (based on frequency)
   - Queue assets for crawling
2. Implement crawl execution:
   - Fetch URL
   - Extract content
   - Store snapshot
   - Update last crawl timestamp
3. Add logging for crawl events
4. Handle errors gracefully (log and continue)

**Deliverable**: Automated crawling based on schedule

**Test**: Run scheduler and verify crawls execute at correct intervals

---

### Phase 3: Diff Engine (Days 5-6)

#### Step 3.1: Basic Diff
**Goal**: Detect when content has changed

**Tasks**:
1. Implement hash comparison:
   - Compare current snapshot hash with previous
   - Skip diff if hash matches
2. Implement text diff using `difflib`:
   - Line-by-line comparison
   - Identify added/removed/modified sections
   - Generate diff output
3. Create change detection trigger:
   - When hash differs, trigger diff engine
   - Pass before/after snapshots to diff engine

**Deliverable**: Can detect when content has changed

**Test**: Compare two snapshots and verify change detection

---

#### Step 3.2: Semantic Diff
**Goal**: Identify meaningful changes (ignore noise)

**Tasks**:
1. Implement structured data comparison:
   - For pricing: Compare pricing tiers, prices, features
   - For features: Compare feature lists
   - For changelog: Compare entries
2. Implement LLM-based semantic diff:
   - Create prompt template for change detection
   - Send before/after content to LLM
   - Ask LLM to identify significant changes
   - Filter out minor edits, formatting changes
3. Generate before/after summaries:
   - Extract relevant sections (not full page)
   - Format for classification
4. Add noise filtering:
   - Ignore dynamic content (timestamps, counters)
   - Ignore minor copy edits (< 5% change)
   - Ignore formatting-only changes

**Deliverable**: Can identify meaningful changes, filter noise

**Test**: Test with real changes (pricing updates, feature additions)

---

#### Step 3.3: Change Storage
**Goal**: Store detected changes in database

**Tasks**:
1. Create change record when diff detects change:
   - Link to before/after snapshots
   - Store before/after content
   - Store diff metadata (JSON)
   - Set `alert_sent = FALSE`
2. Add change retrieval functions
3. Add change status tracking (pending, classified, alerted)

**Deliverable**: Changes stored and retrievable

**Test**: Verify changes are stored correctly in database

---

### Phase 4: Classifier (Days 7-8)

#### Step 4.1: Change Classification
**Goal**: Classify changes and assign priority

**Tasks**:
1. Implement LLM-based change classifier:
   - Create prompt template with:
     - Before/after content
     - Asset type context
     - Priority rules (from ARCHITECTURE.md)
     - Output schema (JSON)
   - Call LLM API with structured output
2. Extract classification results:
   - Change type (pricing, feature, compliance, etc.)
   - Priority (High/Medium/Low)
   - Summary (≤3 sentences)
   - "Why it matters" explanation
3. Update change record with classification
4. Handle LLM API errors gracefully

**Deliverable**: Changes classified with priority and insights

**Test**: Test classification with various change types

---

#### Step 4.2: Quality Gate
**Goal**: Filter out low-signal changes

**Tasks**:
1. Implement quality validation:
   - Check summary length (≤3 sentences)
   - Validate "why it matters" is non-speculative
   - Ensure before/after is clear
   - Reject if classification confidence is low
2. Add quality scoring (optional):
   - Score change significance (0-1)
   - Reject if below threshold (e.g., 0.3)
3. Log rejected changes for review
4. Update change status (approved/rejected)

**Deliverable**: Only high-quality changes proceed to alerting

**Test**: Test with various changes, verify quality filtering

---

### Phase 5: Alerting (Days 9-10)

#### Step 5.1: Slack Integration
**Goal**: Send alerts to Slack

**Tasks**:
1. Set up Slack webhook:
   - Get webhook URL from Slack
   - Add to environment variables
   - Test webhook connection
2. Implement message formatter:
   - Create function to format message per fixed schema:
     - Company
     - Priority
     - Asset
     - Change Type
     - Summary (Before → After)
     - Why It Matters
     - Citation (URL + timestamp)
   - Use Slack Block Kit for formatting
3. Implement webhook sender:
   - Send formatted message to Slack
   - Handle errors (rate limits, invalid webhook)
   - Log delivery status

**Deliverable**: Can send formatted alerts to Slack

**Test**: Send test alert and verify format matches schema

---

#### Step 5.2: Alert Manager
**Goal**: Route alerts based on priority and schedule

**Tasks**:
1. Implement priority-based routing:
   - High priority → immediate delivery
   - Medium priority → queue for daily digest
   - Low priority → queue for weekly summary
2. Implement immediate delivery:
   - Send high-priority alerts within 5 minutes
   - Update `alert_sent` flag
   - Record delivery timestamp
3. Implement daily digest:
   - Aggregate medium-priority changes from last 24 hours
   - Format as single message with sections
   - Send at 9 AM daily
   - Update alert status for all included changes
4. Implement weekly summary:
   - Aggregate low-priority changes from last 7 days
   - Group by competitor
   - Format as digest
   - Send Monday 9 AM
5. Add alert deduplication:
   - Prevent duplicate alerts for same change
   - Track sent alerts

**Deliverable**: Alerts delivered based on priority and schedule

**Test**: Test immediate, daily, and weekly delivery

---

### Phase 6: Integration & Testing (Days 11-12)

#### Step 6.1: End-to-End Integration
**Goal**: Connect all components into working system

**Tasks**:
1. Create main application entry point:
   - Initialize database
   - Load configuration
   - Start scheduler
   - Connect crawler → diff → classifier → alerting
2. Implement main loop:
   - Run crawler on schedule
   - Process detected changes
   - Classify and alert
   - Handle errors gracefully
3. Add comprehensive logging:
   - Log crawl events
   - Log change detections
   - Log classification results
   - Log alert deliveries
   - Log errors with context
4. Add error handling:
   - Retry failed crawls
   - Handle LLM API failures
   - Handle Slack delivery failures
   - Continue processing on errors

**Deliverable**: Fully integrated system running end-to-end

**Test**: Run system for 24 hours with test competitors

---

#### Step 6.2: Testing & Validation
**Goal**: Validate system accuracy and reliability

**Tasks**:
1. Test with real competitor URLs:
   - Add 2-3 test competitors
   - Run crawls and verify content extraction
   - Manually trigger changes (if possible) and verify detection
2. Validate alert quality:
   - Review alerts for accuracy
   - Check for false positives (noise)
   - Verify priority assignments
   - Validate summary quality
3. Tune LLM prompts:
   - Refine classification prompts for accuracy
   - Adjust quality thresholds
   - Test edge cases
4. Performance testing:
   - Test crawl performance
   - Test LLM API latency
   - Verify rate limiting works
5. Add monitoring:
   - Log key metrics (crawl success rate, alert count)
   - Add health checks

**Deliverable**: System validated and tuned

**Test**: Run for 1 week and review all alerts

---

#### Step 6.3: Documentation
**Goal**: Document system for operation

**Tasks**:
1. Update README.md:
   - Setup instructions
   - Configuration guide
   - Running the system
   - Troubleshooting
2. Document configuration format:
   - Competitor config examples
   - Asset type definitions
   - Frequency options
3. Add code comments:
   - Document key functions
   - Explain design decisions
4. Create troubleshooting guide:
   - Common issues and solutions
   - How to debug crawl failures
   - How to review alerts

**Deliverable**: Complete documentation

---

### Phase 7: Deployment (Day 13)

#### Step 7.1: Deployment Setup
**Goal**: Prepare system for production deployment

**Tasks**:
1. Create deployment script:
   - Environment setup
   - Database initialization
   - Configuration validation
2. Set up environment variables:
   - LLM API keys
   - Slack webhook URL
   - Database path (if not SQLite default)
3. Test deployment:
   - Test in clean environment
   - Verify all dependencies install
   - Test configuration loading
4. Set up basic monitoring:
   - Log file rotation
   - Error alerting (optional)
5. Create run script:
   - Start system as daemon/service
   - Or provide instructions for cron/systemd

**Deliverable**: System ready for deployment

**Test**: Deploy to test environment and run for 24 hours

---

## Testing Checklist

### Unit Tests
- [ ] Configuration loading and validation
- [ ] Content extraction for each asset type
- [ ] Hash comparison and diff detection
- [ ] Change classification logic
- [ ] Message formatting

### Integration Tests
- [ ] Crawl → snapshot storage
- [ ] Diff → change detection
- [ ] Classification → priority assignment
- [ ] Alert → Slack delivery

### End-to-End Tests
- [ ] Full pipeline with test competitor
- [ ] Priority-based alert routing
- [ ] Daily digest generation
- [ ] Weekly summary generation

### Manual Validation
- [ ] Review 10+ alerts for quality
- [ ] Verify no false positives
- [ ] Check priority assignments are correct
- [ ] Validate "why it matters" explanations

## Success Criteria

- ✅ System crawls all configured assets on schedule
- ✅ Detects meaningful changes (not noise)
- ✅ Classifies changes correctly (High/Medium/Low)
- ✅ Generates quality insights (≤3 sentences, clear "why it matters")
- ✅ Delivers alerts per priority schedule
- ✅ Slack messages match fixed schema
- ✅ <10% false positive rate
- ✅ 99%+ crawl success rate
- ✅ High-priority alerts within 5 minutes

## Next Steps After V1

Once V1 is validated and running:
1. Monitor for 2-4 weeks to gather feedback
2. Tune LLM prompts based on alert quality
3. Adjust priority rules if needed
4. Consider adding more competitors
5. Plan V2 features (if needed)

