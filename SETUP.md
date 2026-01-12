# Setup Guide

## Initial Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root (same directory as `README.md`) with the following content:

```bash
# LLM API Configuration (choose one)
OPENAI_API_KEY=sk-your-openai-api-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Slack Webhook Configuration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here

# Twitter API Configuration (optional)
TWITTER_BEARER_TOKEN=your-bearer-token-here

# News API Configuration (optional, for news source monitoring)
NEWS_API_KEY=your-news-api-key-here

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///watchdog.db
```

### 3. Configure Competitors

Copy the example configuration and edit it:

```bash
cp config/competitors.example.yaml config/competitors.yaml
```

Edit `config/competitors.yaml` with your competitor URLs and assets to monitor.

### 4. Initialize Database

```bash
python -m src.storage.init_db
```

This will create the SQLite database with all required tables.

### 5. Test Configuration

Run the main script to verify everything is set up correctly:

```bash
python -m src.main
```

You should see:
- Database initialization success
- Configuration loaded with competitor count
- System ready message

## Next Steps

Once Phase 1 is complete, you can proceed to Phase 2 (Crawler) implementation.

## Troubleshooting

### Import Errors
If you see import errors, make sure:
1. Virtual environment is activated
2. Dependencies are installed: `pip install -r requirements.txt`

### Configuration Errors
If configuration loading fails:
1. Check that `config/competitors.yaml` exists
2. Validate YAML syntax
3. Ensure all required fields are present (see `config/competitors.example.yaml`)

### Database Errors
If database initialization fails:
1. Check file permissions in project directory
2. Ensure SQLite is available (usually built into Python)
