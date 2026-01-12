# Twitter Search API Integration

## Overview

The system now supports monitoring Twitter/X using the Twitter API v2 search endpoint (`GET /2/tweets/search/recent`). This allows you to search for recent tweets related to competitors using search queries.

## Setup

### 1. Get Twitter API Bearer Token

1. Apply for Twitter API access at https://developer.twitter.com/
2. Create a new app in the Twitter Developer Portal
3. Generate a Bearer Token (read-only access is sufficient)
4. Add to `.env` file:
   ```bash
   TWITTER_BEARER_TOKEN=your-bearer-token-here
   ```

### 2. Install Dependencies

```bash
pip install tweepy>=4.14.0
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

### Basic Configuration

Add Twitter monitoring to your `config/competitors.yaml`:

```yaml
competitors:
  - name: "DocuSign"
    base_url: "https://www.docusign.com"
    assets:
      # ... other assets ...
      
      - type: "twitter"
        url: "https://twitter.com/docusign"  # For reference only
        query: "from:docusign OR @docusign OR \"DocuSign\" -is:retweet lang:en"
        crawl_frequency: "daily"
        priority_threshold: "medium"
```

### Query Syntax

The `query` field uses Twitter's search query syntax. Common operators:

- `from:username` - Tweets from a specific user
- `@username` - Tweets mentioning a user
- `"exact phrase"` - Exact phrase match
- `-is:retweet` - Exclude retweets
- `lang:en` - Language filter (English)
- `OR` - Logical OR operator
- `AND` - Logical AND operator (default)

### Example Queries

**Monitor competitor's official account:**
```yaml
query: "from:competitor_name -is:retweet lang:en"
```

**Monitor mentions and official account:**
```yaml
query: "from:competitor_name OR @competitor_name OR \"Competitor Name\" -is:retweet lang:en"
```

**Monitor product-specific tweets:**
```yaml
query: "from:competitor_name (\"new feature\" OR \"product launch\" OR \"pricing\") -is:retweet lang:en"
```

**Monitor competitor and related keywords:**
```yaml
query: "(from:competitor_name OR \"Competitor Name\") (\"e-signature\" OR \"document signing\") -is:retweet lang:en"
```

## How It Works

1. **Crawl:** Uses Twitter API v2 `search_recent_tweets` endpoint
2. **Extract:** Gets recent tweets matching the query (up to 100 per request)
3. **Compare:** Detects new tweets by comparing tweet IDs
4. **Classify:** Assigns priority based on content
5. **Alert:** Sends Slack notification for new tweets

## API Endpoint

The system uses:
- **Endpoint:** `GET /2/tweets/search/recent`
- **Method:** `tweepy.Client.search_recent_tweets()`
- **Max Results:** 100 tweets per request (API limit)
- **Fields:** `created_at`, `public_metrics`, `author_id`, `text`
- **Expansions:** `author_id` (to get username)

## Rate Limits

Twitter API v2 has rate limits:
- **Free tier:** 300 requests per 15 minutes
- **Basic tier:** 300 requests per 15 minutes
- **Pro tier:** Higher limits

The system respects rate limits and will log errors if limits are exceeded.

## Change Detection

- **New tweets:** Detected by comparing tweet IDs between snapshots
- **Structured diff:** Shows new tweets with text, date, author, engagement metrics
- **Priority:** Medium (default) - tweets often contain announcements

## Priority Rules

- **High:** Product launches, major partnerships, pricing announcements
- **Medium:** General updates, feature announcements, customer wins (default)
- **Low:** Social engagement, general commentary

## Error Handling

The system handles:
- **Rate limit exceeded:** Logs warning, returns empty results
- **Authentication errors:** Logs error, raises exception
- **API errors:** Logs error, returns empty results
- **Missing query:** Raises ValueError

## Troubleshooting

### "TWITTER_BEARER_TOKEN not found"
- Add `TWITTER_BEARER_TOKEN` to your `.env` file
- Get token from Twitter Developer Portal

### "tweepy is required"
- Install: `pip install tweepy>=4.14.0`

### "Rate limit exceeded"
- Wait 15 minutes before retrying
- Consider upgrading Twitter API tier
- Reduce crawl frequency

### "No tweets found"
- Check query syntax
- Verify competitor's Twitter handle
- Ensure tweets exist matching the query
- Check if query is too restrictive

## Example Configuration

```yaml
competitors:
  - name: "DocuSign"
    base_url: "https://www.docusign.com"
    assets:
      - type: "twitter"
        url: "https://twitter.com/docusign"
        query: "from:docusign OR @docusign OR \"DocuSign\" -is:retweet lang:en"
        crawl_frequency: "daily"
        priority_threshold: "medium"
      
      - type: "twitter"
        url: "https://twitter.com/search"
        query: "from:docusign (\"new feature\" OR \"product launch\" OR \"pricing change\") -is:retweet lang:en"
        crawl_frequency: "daily"
        priority_threshold: "high"
```

## Notes

- The `url` field is for reference only (not used for API calls)
- The `query` field is required for Twitter assets
- If `query` is not provided, system will auto-generate from competitor name
- Tweets are stored with full metadata (text, date, author, engagement metrics)
- Only new tweets (not seen before) trigger alerts
