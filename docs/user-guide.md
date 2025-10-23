# News Llama User Guide

Welcome to News Llama! This guide will help you get started with creating your personalized AI-powered news digest.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Your Profile](#creating-your-profile)
3. [Managing Your Interests](#managing-your-interests)
4. [Viewing Newsletters](#viewing-newsletters)
5. [Understanding Newsletter Status](#understanding-newsletter-status)
6. [Daily Automation](#daily-automation)
7. [FAQ](#faq)
8. [Tips & Best Practices](#tips--best-practices)
9. [Troubleshooting](#troubleshooting)

## Getting Started

### What is News Llama?

News Llama is an AI-powered news curation service that:
- **Aggregates** news from multiple sources (RSS, Reddit, Hacker News, Twitter/X)
- **Discovers** new sources based on your interests
- **Summarizes** articles using AI for quick reading
- **Personalizes** your daily news digest based on your preferences

### Accessing News Llama

1. Open your web browser
2. Navigate to your News Llama URL (e.g., `http://news-llama.example.com`)
3. You'll see the profile selection page

## Creating Your Profile

### Step 1: Click "Create New Profile"

From the homepage, select the "Create New Profile" button to get started.

### Step 2: Enter Your Name

Provide your first name. This helps personalize your experience and lets you switch between multiple profiles if needed.

### Step 3: Select Your Interests

Choose topics you want to follow. You can:

**Select from Predefined Interests:**
- AI
- rust
- LocalLLM
- LocalLlama
- strix halo
- startups
- technology
- programming
- machine learning
- web development

**Add Custom Interests:**
- Type any topic in the "Add custom interest" field
- Press Enter or click "Add" to include it
- Examples: "climate change", "electric vehicles", "quantum computing", "NBA"

**Tips for Good Interests:**
- Be specific: "machine learning" is better than "computers"
- Use common names: "AI" works better than "artificial intelligence systems"
- Include multiple variations: Add both "rust" and "rust programming" for better coverage

### Step 4: Submit

Click "Create Profile" to complete setup. Your first newsletter will start generating immediately!

**What Happens Next:**
- You'll be redirected to your calendar view
- A toast notification confirms your first newsletter is being generated
- Generation takes **10-15 minutes** depending on your interests
- You can continue browsing while it generates in the background

## Managing Your Interests

### Accessing Profile Settings

1. Click your **profile icon** in the top-right corner
2. Select **"Profile Settings"** from the dropdown menu

### Adding Interests

**Method 1: Select from Available Interests**
1. Click the "+" button next to any available interest
2. It's instantly added to your profile
3. Today's newsletter automatically regenerates with the new interest

**Method 2: Add Custom Interest**
1. Type the interest name in the text field
2. Click "Add Interest" or press Enter
3. The interest appears in your list immediately

**What Happens When You Add an Interest:**
- The interest is saved to your profile
- If you already have a newsletter for today, it's marked for regeneration
- The system will create a new version incorporating content about your new interest
- This process takes 10-15 minutes

### Removing Interests

1. Find the interest in your "Current Interests" list
2. Click the **×** button next to the interest name
3. Confirm removal (if prompted)
4. Today's newsletter regenerates without that topic

**Note:** You must have at least one interest. You cannot remove your last interest.

### Updating Your Name

1. Go to Profile Settings
2. Click "Edit Name"
3. Enter your new name
4. Click "Save"

## Viewing Newsletters

### Calendar View

The calendar view shows all your newsletters organized by month:

**Navigation:**
- **◀ Previous Month**: View older newsletters
- **Current Month**: Today's month is displayed by default
- **Next Month ▶**: View future dates (for scheduled newsletters)

**Date Tiles:**
Each date shows:
- **Status Icon**: 🟢 Completed / 🟡 Generating / 🔴 Failed
- **Date Number**: Click to view that newsletter
- **Empty Dates**: Click to generate a newsletter for that day

### Opening a Newsletter

1. Click any **completed** (🟢) date on the calendar
2. The newsletter opens in a new page showing:
   - Your interests for that day
   - Articles grouped by category
   - AI-generated summaries and key points
   - Source attribution and discovery information
   - Sentiment analysis and importance scores

### Newsletter Content

Each newsletter includes:

**Header:**
- Your name and the date
- List of your interests
- Discovery statistics (how many sources were found)

**Articles:**
For each article, you'll see:
- **Title**: Clickable link to original source
- **Summary**: ~200-500 word AI-generated summary
- **Key Points**: 5-7 bullet points highlighting main takeaways
- **Sentiment**: Positive/Neutral/Negative analysis of the article's tone
- **Importance Score**: 0.0-1.0 rating of relevance to your interests
- **Source**: Where the article came from (e.g., r/rust, Hacker News, @sama)
- **Discovery Badge**: If the source was AI-discovered, shows reasoning

**Categories:**
Articles are grouped by your interests, making it easy to jump to topics you care about most.

### Sharing Newsletters

To share a newsletter:
1. Open the newsletter
2. Copy the URL from your browser (e.g., `/newsletters/news-2025-10-22`)
3. Share the URL with others

**Note:** Currently, newsletters are accessible to anyone with the link. If your News Llama instance is private, ensure you only share with authorized users.

## Understanding Newsletter Status

### Status Icons

| Icon | Status | Meaning |
|------|--------|---------|
| 🟢 | **Completed** | Newsletter is ready to view |
| 🟡 | **Generating** | Newsletter is currently being created (10-15 min) |
| 🔴 | **Failed** | Generation encountered an error |
| 🔵 | **Pending** | Scheduled but not yet started |

### Status Details

#### Completed (🟢)
- Newsletter has been generated successfully
- Click the date to view your personalized digest
- Newsletter is cached for fast loading

#### Generating (🟡)
- The system is:
  1. Discovering sources based on your interests
  2. Aggregating articles from RSS, Reddit, Hacker News, Twitter
  3. Removing duplicates and filtering low-quality content
  4. Summarizing articles with AI
  5. Generating the final HTML newsletter

- **Typical Duration**: 10-15 minutes
- **Factors Affecting Speed**:
  - Number of interests (more interests = more sources to check)
  - LLM server performance
  - API response times from Reddit/Twitter

- **What to Do**: Check back in 15 minutes, or wait for the status to change

#### Failed (🔴)
- Something went wrong during generation
- Common causes:
  - LLM server offline or slow
  - Network connectivity issues
  - API rate limits exceeded
  - No articles found for your interests

- **What to Do**:
  - Click the date tile
  - Click "Retry" button to try again
  - If it fails repeatedly, contact your system administrator

#### Pending (🔵)
- Newsletter is scheduled but hasn't started generating yet
- Usually applies to future dates you've manually queued
- Will automatically transition to "Generating" when processing begins

### Retry Logic

Failed newsletters automatically retry:
- **Attempt 1**: Immediate generation
- **Attempt 2**: After 5 minutes (if first attempt fails)
- **Attempt 3**: After 15 minutes (if second attempt fails)
- **Max Retries**: 3 attempts total

After 3 failures, the newsletter remains in "Failed" status and requires manual retry.

## Daily Automation

### How It Works

News Llama automatically generates newsletters for all users every day:

**Default Schedule:**
- **Time**: 6:00 AM Pacific Time
- **Frequency**: Once per day
- **Users**: All users with at least one interest

**What Happens:**
1. At 6:00 AM, the scheduler wakes up
2. For each user, it checks if today's newsletter exists
3. If not, it creates a new newsletter with status "pending"
4. The newsletter enters the generation queue
5. Within 15 minutes, your fresh newsletter is ready

### Customization (Administrator Only)

Your system administrator can adjust:
- **Time**: Any hour and minute (e.g., 8:30 AM)
- **Timezone**: Any timezone (e.g., America/New_York, Europe/London)
- **Enabled/Disabled**: Turn off automation if you prefer manual generation

To check your scheduler status, ask your administrator to visit: `/health/scheduler`

### Manual Generation

Don't want to wait for the daily automation? Generate newsletters manually:

1. Go to your calendar
2. Click any **empty date** (no status icon)
3. A newsletter starts generating immediately
4. Status changes to 🟡 Generating

**Rate Limits:**
- You can generate up to **10 newsletters per hour**
- This prevents accidental abuse and server overload
- If you hit the limit, wait 60 seconds and try again

## FAQ

### How long does newsletter generation take?

**Typical Time**: 10-15 minutes

**Why So Long?**
- News Llama fetches articles from dozens of sources
- Each article is processed and cleaned
- Duplicates are detected and removed
- AI summarizes 50-100 articles (this is the slowest part)
- Final HTML is generated with all formatting

**Can It Be Faster?**
- Fewer interests = faster generation (fewer sources to check)
- Pre-filtering limits articles per category (default: 10)
- LLM server performance is the main bottleneck

### Can I have multiple interests?

**Yes!** Add as many interests as you want. However:
- More interests = more sources = longer generation time
- Recommended: 5-10 interests for best balance
- You can always add/remove interests later

### What if no articles are found for my interest?

If News Llama can't find articles for an interest:
- That interest's section will be empty in the newsletter
- Other interests will still show articles
- Try adding related variations (e.g., "AI", "artificial intelligence", "machine learning")

### Can I delete old newsletters?

Currently, newsletters persist indefinitely. If you want to clean up old newsletters, contact your system administrator. They can:
- Delete newsletters older than X days
- Remove newsletters manually from the database
- Set up automatic cleanup policies

### Can I export newsletters?

Each newsletter is a standalone HTML file. To export:
1. Open the newsletter
2. Right-click → "Save Page As"
3. Choose "Webpage, Complete" to save HTML + images
4. Or print to PDF using your browser's print function

### Can other people see my newsletters?

**Depends on your setup:**
- **Private instance**: Only users with access to the News Llama server can view newsletters
- **Public instance**: Anyone with the newsletter URL can view it
- **Newsletter content**: Not protected by authentication (currently)

Ask your administrator if you need private newsletters.

### What happens if I remove all my interests?

You cannot remove your last interest. The system requires at least one interest to generate meaningful newsletters. If you try to remove your last interest, you'll see an error message.

### Can I switch between multiple profiles?

Yes! News Llama supports multiple profiles:
1. Go to the homepage (click "News Llama" logo)
2. Select a different profile from the list
3. Or create a new profile

Each profile has:
- Its own interests
- Its own newsletter history
- Its own settings

Use cases:
- **Work vs Personal**: Separate "AI research" profile from "NBA news" profile
- **Shared Server**: Multiple family members with different interests
- **Testing**: Try different interest combinations

### What sources does News Llama check?

News Llama aggregates from:

**Always Checked:**
- **RSS Feeds**: Blogs, news sites, podcasts
- **Hacker News**: Top stories and new posts
- **Reddit**: Subreddits related to your interests
- **AI-Discovered Sources**: LLM finds sources based on your interests

**Optional (if configured):**
- **Twitter/X**: Tweets from relevant accounts
- **Web Search**: Real-time Google/Bing search results

**Source Discovery:**
- Pre-defined patterns for common topics (AI → r/MachineLearning, @sama, etc.)
- AI-powered discovery for niche interests (e.g., "strix halo" → r/AMD, r/hardware)

### Why do some articles have "Discovered by AI" badges?

These sources were found by the AI source discovery engine:
1. You add an interest (e.g., "quantum computing")
2. AI analyzes your interest and searches for relevant sources
3. It finds subreddits, Twitter accounts, RSS feeds you might not know about
4. These sources are marked with "AI Discovered" and show the reasoning

Benefits:
- Discover niche communities you didn't know existed
- Get broader coverage beyond pre-defined sources
- See why the AI thinks a source is relevant

## Tips & Best Practices

### Choosing Good Interests

✅ **Do:**
- Be specific: "rust programming", "NBA playoffs", "climate policy"
- Use common terminology: "AI" rather than "artificial general intelligence"
- Include multiple related terms: "startups", "venture capital", "YCombinator"
- Add emerging topics: "strix halo", "o3 model", "llama 4"

❌ **Avoid:**
- Too generic: "news", "technology", "science" (too broad, noisy results)
- Too niche: "my local coffee shop" (unlikely to have articles)
- Misspellings: "technologyy", "programing" (won't find sources)

### Optimizing Generation Time

- **Start Small**: Begin with 3-5 interests, add more later
- **Use Predefined Interests**: These are optimized for fast discovery
- **Remove Inactive Interests**: If an interest never returns articles, remove it
- **Avoid Duplicates**: Don't add "AI", "artificial intelligence", "A.I." separately (one is enough)

### Making the Most of Your Newsletter

- **Read Key Points First**: Get the gist in 30 seconds per article
- **Use Importance Scores**: Focus on 0.8+ importance articles first
- **Click Through on Interesting Topics**: Full articles have more depth
- **Check Discovery Stats**: See which sources are most productive
- **Adjust Interests Regularly**: Add trending topics, remove stale ones

### Sharing and Collaboration

- **Share Individual Articles**: Copy the article URL from the newsletter
- **Share Full Newsletters**: Copy the `/newsletters/{guid}` URL
- **Discuss with Team**: Use newsletters as a starting point for team discussions
- **Archive Good Content**: Save newsletters that were particularly valuable

### Managing Your Workflow

**Morning Routine:**
1. Open News Llama (your newsletter is ready at 6 AM)
2. Skim the table of contents (categories)
3. Read key points for all high-importance articles (5-10 min)
4. Bookmark 2-3 articles for deep reading later
5. Adjust interests if needed for tomorrow

**Weekly Review:**
1. Every Friday, review your interests
2. Remove topics that never return good articles
3. Add new emerging topics you heard about this week
4. Check your generation success rate (`/health/generation`)

## Troubleshooting

### "Failed to Generate Newsletter"

**Possible Causes:**
- LLM server is offline or slow
- No articles found for your interests
- Network connectivity issues
- API rate limits exceeded

**Solutions:**
1. Click "Retry" on the failed newsletter
2. Wait 15 minutes and try again
3. Check that you have at least one interest
4. Try removing very niche interests temporarily
5. Contact your administrator if it persists

### "Rate Limit Exceeded"

**What This Means:**
You've generated more than 10 newsletters in the past 60 minutes.

**Solutions:**
- Wait 60 seconds and try again
- Don't spam the generate button
- Check your calendar to avoid generating duplicates

**Why This Exists:**
Rate limiting prevents accidental server overload (e.g., clicking "Generate" 100 times).

### Newsletter Stuck on "Generating"

**If It's Been Less Than 20 Minutes:**
- This is normal! Be patient, especially if you have many interests.

**If It's Been More Than 30 Minutes:**
1. Refresh the page to check if status updated
2. Check `/health/scheduler` (ask your admin for access)
3. Look for errors in the system logs
4. Restart the generation by marking it failed and retrying

**Contact Your Administrator If:**
- Multiple newsletters are stuck for hours
- The issue happens repeatedly
- Generation never completes, even with simple interests

### Newsletter Has No Articles

**Possible Reasons:**
- Your interests are too niche (no sources found)
- All discovered sources had no recent articles
- Articles were filtered out (duplicates, low quality, extraction failures)

**Solutions:**
1. Add more common/popular interests
2. Add multiple variations of an interest
3. Check back tomorrow (some topics don't have daily articles)
4. Use broader terms (e.g., "technology" instead of "quantum networking protocols")

### Can't Add or Remove Interests

**If Add Button is Disabled:**
- You may already have that interest
- The interest name is invalid (too short, special characters)

**If Remove Button is Disabled:**
- You're trying to remove your last interest (not allowed)
- You need at least one interest to use News Llama

**Solutions:**
- Check the error message displayed
- Add a new interest before removing your last one
- Refresh the page and try again

### Profile Not Found

**What Happened:**
Your browser cookie expired or was deleted.

**Solutions:**
1. Go to the homepage
2. Select your profile again
3. Your data is safe—only the session cookie was lost

**To Avoid This:**
- Don't clear browser cookies frequently
- Bookmark the calendar page (not individual newsletters)
- Ask your admin about longer session cookies if this happens often

### Newsletter Content Seems Wrong

**If Articles Don't Match Your Interests:**
- The AI may have misunderstood your interest term
- Try rephrasing (e.g., "rust programming" instead of "rust")
- Check which sources were discovered (`/newsletters/{guid}`)

**If Summaries Are Inaccurate:**
- This is an LLM limitation, not a bug
- Read the full article for accurate details
- Report particularly bad summaries to your admin for fine-tuning

**If Articles Are Duplicates:**
- Duplicate detection is 80-90% accurate, not perfect
- Very similar articles from different sources may appear
- This is normal and shows comprehensive coverage

### Browser Issues

**Newsletter Won't Load:**
- Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- Clear browser cache
- Try a different browser (Chrome, Firefox, Safari)

**Layout Looks Broken:**
- Your browser may be blocking CSS/JavaScript
- Check browser console for errors (F12 → Console)
- Ensure you're using a modern browser (Chrome 90+, Firefox 88+, Safari 14+)

## Getting Help

### System Status

Check the health endpoints (ask your admin for access):
- **Scheduler Status**: `/health/scheduler` - Shows if daily generation is working
- **Generation Metrics**: `/health/generation` - Success/failure rates and timing

### Contacting Support

If you encounter persistent issues:
1. Note the exact error message (screenshot if possible)
2. Note the date/time the issue occurred
3. Note which newsletter (GUID) is affected
4. Describe the steps you took before the error
5. Contact your system administrator or file a GitHub issue

### Additional Resources

- **README**: [../README.md](../README.md) - Overview and CLI usage
- **Deployment Guide**: [deployment.md](deployment.md) - For administrators
- **Architecture Docs**: [architecture.md](architecture.md) - Technical details
- **GitHub Issues**: Report bugs and request features

---

## Welcome to Smarter News Consumption! 📰🦙

News Llama helps you stay informed without the overwhelm. By curating and summarizing content based on your interests, you can:
- **Save Time**: Read 10 articles in the time it takes to read 2
- **Discover More**: AI finds sources you wouldn't discover manually
- **Stay Focused**: Only see news about topics you care about
- **Reduce Noise**: Skip clickbait, ads, and irrelevant content

We hope you enjoy using News Llama. Happy reading!
