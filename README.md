# AI Competitor Watchdog V1

An AI-powered system that monitors competitor web assets and delivers competitive intelligence alerts via Slack.

## Overview

This system automatically tracks and monitors competitor web assets in the contract management & e-signature space, detecting meaningful changes and delivering prioritized alerts to your Slack channel.

## Features

- **Automated Monitoring**: Crawls competitor websites on configurable schedules
- **Intelligent Change Detection**: Uses AI to identify meaningful changes (filters noise)
- **Priority-Based Alerts**: Categorizes changes as High/Medium/Low priority
- **Slack Integration**: Delivers alerts via Slack with structured format
- **Multiple Asset Types**: Monitors pricing, features, changelogs, news, blogs, compliance pages, Twitter/X (via search API)

## Quick Start

### Prerequisites

- Python 3.11 or higher
- OpenAI API key (or Anthropic API key)
- Slack webhook URL

### Installation

1. Clone or download this repository

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys and Slack webhook URL
```

5. Configure competitors:
```bash
cp config/competitors.example.yaml config/competitors.yaml
# Edit config/competitors.yaml with your competitor URLs
```

6. Initialize the database:
```bash
python -m src.storage.init_db
```

7. Run the system:
```bash
# Run a single crawl cycle (for testing)
python -m src.main --crawl-once

# Start the scheduler (runs continuously, includes alert scheduler)
python -m src.main --start-scheduler

# Start only the alert scheduler (for separate deployment)
python -m src.main --start-alert-scheduler

# Or just run (defaults to starting scheduler)
python -m src.main
```

## Configuration

### Competitor Configuration

Edit `config/competitors.yaml` to add competitors and their assets to monitor. See `config/competitors.example.yaml` for the format.

### Environment Variables

See `.env.example` for all available configuration options. Required variables:
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- `SLACK_WEBHOOK_URL`

## Architecture

See `ARCHITECTURE.md` for detailed system architecture and design decisions.

## Build Plan

See `BUILD_PLAN.md` for the step-by-step implementation plan.

## Project Structure

```
ai-competitor-watchdog/
├── config/
│   ├── competitors.yaml          # Competitor configuration
│   └── competitors.example.yaml   # Example configuration
├── src/
│   ├── crawler/                   # Web crawling components
│   ├── diff/                      # Change detection engine
│   ├── classifier/                # AI classification
│   ├── alerting/                  # Slack alerting
│   ├── storage/                   # Database layer
│   └── main.py                    # Main entry point
├── ARCHITECTURE.md                # System architecture
├── BUILD_PLAN.md                  # Build plan
├── QUICK_REFERENCE.md             # Quick reference guide
└── requirements.txt               # Python dependencies
```

## Status

✅ **Phase 1 Complete**: Foundation (Database, Configuration)  
✅ **Phase 2 Complete**: Crawler (Web crawler, Content extractors, Scheduler)  
✅ **Phase 3 Complete**: Diff Engine (Change detection, Semantic analysis)  
✅ **Phase 4 Complete**: Classifier (Priority assignment, Quality gate)  
✅ **Phase 5 Complete**: Alerting (Slack integration, Alert manager)  

🎉 **V1 Complete!** All phases implemented and ready for use.  

See BUILD_PLAN.md for detailed progress.

## License

[Add your license here]

