# News API Integration

## Overview

The system now supports monitoring news sources using NewsAPI.org. This allows you to search for recent news articles related to competitors.

## Setup

### 1. Get NewsAPI.org API Key

1. Sign up for a free account at https://newsapi.org/
2. Get your API key from the dashboard
3. Add to `.env` file:
   ```bash
   NEWS_API_KEY=pub_ac21c89ed0344fd7a9b76a1cdd8f8ad1
   ```

**Note**: Free tier limitations:
- 100 requests per day
- Articles from last 1 month only
- No commercial use

### 2. Install Dependencies

The `requests` library is already included in `requirements.txt`. No additional installation needed.

## Configuration

### Basic Configuration

Add news monitoring to your `config/competitors.yaml`:

```yaml
competitors:
  - name: "DocuSign"
    base_url: "https://www.docusign.com"
    assets:
      # ... other assets ...
      
      - type: "news"
        url: "https://newsapi.org"  # For reference only
        query: "DocuSign OR docusign OR \"electronic signature\""  # Optional: custom query
        crawl_frequency: "daily"
        priority_threshold: "medium"
```

### Query Options

- **With query**: Use a custom search query
  ```yaml
  query: "DocuSign OR docusign OR \"electronic signature\""
  ```

- **Without query**: System will use competitor name as the search query
  ```yaml
  # query field can be omitted
  ```

### Query Syntax

NewsAPI.org supports:
- **Keywords**: `DocuSign`
- **Phrases**: `"electronic signature"`
- **OR operator**: `DocuSign OR docusign`
- **AND operator**: `DocuSign AND pricing` (implicit)

## How It Works

1. **Crawling**: The system calls NewsAPI.org's `/everything` endpoint
2. **Search**: Searches for articles matching the query from the last 7 days
3. **Storage**: Stores article metadata (title, description, URL, published date, source)
4. **Change Detection**: Compares new articles against previous snapshots
5. **Alerts**: Sends alerts for new articles that meet priority thresholds

## Article Data Structure

Each article includes:
- `title`: Article headline
- `description`: Article summary/description
- `url`: Full article URL
- `published_at`: Publication timestamp
- `source`: News source name
- `author`: Article author (if available)
- `content`: Article content preview (truncated to 500 chars)
- `url_to_image`: Article image URL (if available)

## Rate Limits

**Free Tier**:
- 100 requests per day
- 1 month historical data
- No commercial use

**Recommendations**:
- Use `daily` crawl frequency for news assets
- Monitor multiple competitors? Consider upgrading to a paid plan
- The system will log warnings if rate limits are hit

## Troubleshooting

### API Key Not Found
```
WARNING: NEWS_API_KEY not found in .env. News API will not be used.
```
**Solution**: Add `NEWS_API_KEY=your-key-here` to your `.env` file

### Rate Limit Exceeded
```
NewsAPI rate limit reached. Please wait before retrying.
```
**Solution**: 
- Wait 24 hours for free tier reset
- Upgrade to a paid plan for higher limits
- Reduce crawl frequency

### No Articles Found
- Check your query syntax
- Verify the competitor name is spelled correctly
- Try a broader search query
- Check if there are recent articles (last 7 days)

### Authentication Error
```
NewsAPI authentication failed. Check your API key.
```
**Solution**: 
- Verify your API key is correct
- Check if your API key is active in NewsAPI.org dashboard
- Ensure no extra spaces in `.env` file

## Example Queries

```yaml
# Simple competitor name
query: "DocuSign"

# Multiple variations
query: "DocuSign OR docusign OR \"DocuSign Inc\""

# Competitor + keywords
query: "DocuSign AND (pricing OR features OR integration)"

# Industry-specific
query: "electronic signature OR e-signature OR digital signature"
```

## Integration with Change Detection

When new articles are detected:
1. Articles are compared by URL (unique identifier)
2. New articles trigger change detection
3. Changes are classified by priority (High/Medium/Low)
4. Alerts are sent based on priority thresholds

## Best Practices

1. **Query Specificity**: Use specific queries to reduce noise
   - ✅ `"DocuSign" AND pricing`
   - ❌ `DocuSign` (too broad, may include unrelated articles)

2. **Crawl Frequency**: Use `daily` for news (news changes frequently)

3. **Priority Threshold**: Set to `medium` or `low` for news (most news is informational)

4. **Multiple Sources**: Consider adding multiple news assets with different queries for comprehensive coverage
