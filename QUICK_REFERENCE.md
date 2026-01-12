# AI Competitor Watchdog V1 - Quick Reference

## System Overview
AI-powered system that monitors competitor web assets and delivers competitive intelligence alerts via Slack.

## In Scope (V1)
✅ Pricing pages  
✅ Feature/solution pages  
✅ Changelog pages  
✅ Sitemap changes (new URLs)  
✅ News & press releases  
✅ Blogs (product, pricing, AI, compliance only)  
✅ Policy & compliance pages  

## Out of Scope (V1)
❌ Social media monitoring  
❌ Hiring/LinkedIn signals  
❌ Review sites (G2, Capterra)  
❌ Generic thought leadership blogs  
❌ Sentiment analysis  
❌ Dashboards/UI  

## Priority Rules

### High Priority
- Pricing changes
- Free tier introduction/removal
- Major feature launches
- Security/compliance certifications
- Major integrations

### Medium Priority
- Changelog updates
- Press releases
- New case studies
- New customer logos

### Low Priority
- Homepage/landing page copy changes
- General industry blog posts
- Testimonials

## Alert Delivery Schedule
- **High Priority**: Immediate (< 5 minutes)
- **Medium Priority**: Daily digest (9 AM daily)
- **Low Priority**: Weekly summary (Monday 9 AM)

## Slack Alert Format (Fixed Schema)
```
Company: [competitor name]
Priority: [High/Medium/Low]
Asset: [asset type]
Change Type: [pricing/feature/compliance/etc.]
Summary (Before → After): [≤3 sentences]
Why It Matters: [explicit, non-speculative]
Citation (URL + timestamp): [URL] (Detected: [timestamp])
```

## Insight Quality Bar
Only send alert if:
- ✅ Before/after change is detected
- ✅ URL + timestamp included
- ✅ Summary ≤3 sentences
- ✅ "Why it matters" is explicit and non-speculative

## Tech Stack (V1)
- **Language**: Python 3.11+
- **Scraping**: requests + BeautifulSoup4
- **Database**: SQLite (V1)
- **LLM**: OpenAI GPT-4 or Anthropic Claude
- **Scheduling**: schedule library
- **Slack**: Webhook integration

## Key Components
1. **Crawler**: Fetches and extracts content from competitor URLs
2. **Diff Engine**: Detects meaningful changes (filters noise)
3. **Classifier**: Assigns priority and generates insights (LLM-based)
4. **Alert Manager**: Routes and delivers alerts via Slack

## Build Timeline
- **Phase 1**: Foundation (Days 1-2)
- **Phase 2**: Crawler (Days 3-4)
- **Phase 3**: Diff Engine (Days 5-6)
- **Phase 4**: Classifier (Days 7-8)
- **Phase 5**: Alerting (Days 9-10)
- **Phase 6**: Integration & Testing (Days 11-12)
- **Phase 7**: Deployment (Day 13)

## Configuration
- Competitor URLs and assets: `config/competitors.yaml`
- Crawl schedules: Defined per asset in config
- Environment variables: `.env` file (API keys, Slack webhook)

## Success Metrics
- **Accuracy**: >90% meaningful alerts (not noise)
- **Latency**: High-priority alerts within 5 minutes
- **Reliability**: 99%+ crawl success rate
- **Signal Quality**: <10% false positives

## Architecture Documents
- **ARCHITECTURE.md**: Full system architecture, data models, design decisions
- **BUILD_PLAN.md**: Detailed step-by-step build sequence
- **This file**: Quick reference for key concepts

