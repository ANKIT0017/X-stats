import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import os
from datetime import datetime
import re
import sys
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback

NITTER_INSTANCES = [
    os.environ.get("NITTER_INSTANCE") or "https://nitter.net",
]

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_with_selenium(url, timeout=30):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(timeout)
        driver.get(url)

        wait = WebDriverWait(driver, timeout)
        timeline_items = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".timeline-item"))
        )

        data = []
        for item in timeline_items:
            try:
                # Skip retweets
                header = item.find_element(By.CSS_SELECTOR, ".tweet-header").text.lower()
                body   = item.find_element(By.CSS_SELECTOR, ".tweet-body").text.lower()
                if "retweeted" in header or "retweeted" in body:
                    continue

                # Parse date & content
                date    = item.find_element(By.CSS_SELECTOR, ".tweet-date").text.strip()
                content = item.find_element(By.CSS_SELECTOR, ".tweet-content").text.strip()

                # Engagement stats
                stats = {"replies": "0", "retweets": "0", "likes": "0"}
                for cont in item.find_elements(By.CSS_SELECTOR, ".tweet-stats .icon-container"):
                    txt  = cont.text.strip()
                    html = cont.get_attribute("innerHTML")
                    if not txt:
                        continue
                    if "icon-comment" in html:
                        stats["replies"] = txt
                    elif "icon-retweet" in html:
                        stats["retweets"] = txt
                    elif "icon-heart" in html:
                        stats["likes"] = txt

                # **New**: detect actual media elements
                has_media = bool(item.find_elements(
                    By.CSS_SELECTOR,
                    ".attachments img, .media img, .tweet-content img"
                ))

                data.append({
                    "Date":     date,
                    "Tweet":    content,
                    "Replies":  stats["replies"],
                    "Retweets": stats["retweets"],
                    "Likes":    stats["likes"],
                    "HasMedia": has_media
                })

            except Exception:
                # skip any problematic items
                continue

        return data

    except Exception as e:
        print("Error fetching data:", repr(e))
        traceback.print_exc()
        return None

    finally:
        if driver:
            driver.quit()


def fetch_nitter_stats(username, max_tweets=100):
    """
    Fetches up to max_tweets from nitter.net and returns as DataFrame.
    """
    url = f"https://nitter.net/{username}"
    print(f"Fetching: {url}")
    time.sleep(random.uniform(1, 3))

    data = fetch_with_selenium(url)
    if not data:
        print("No data found.")
        return pd.DataFrame([])

    return pd.DataFrame(data[:max_tweets])


def process_tweets(df):
    """
    Process and enrich tweet DataFrame: parse dates, extract features, etc.
    """
    if df.empty:
        return df

    # Convert date strings to datetime
    def parse_date(date_str):
        if 'h' in date_str:
            return datetime.now() - pd.Timedelta(hours=int(date_str.replace('h','')))
        if 'm' in date_str:
            return datetime.now() - pd.Timedelta(minutes=int(date_str.replace('m','')))
        try:
            return pd.to_datetime(date_str)
        except:
            return pd.NaT

    df["Datetime"] = df["Date"].apply(parse_date)
    df["DayOfWeek"] = df["Datetime"].dt.day_name()
    df["Hour"] = df["Datetime"].dt.hour

    # Engagement metrics
    for col in ["Replies", "Retweets", "Likes"]:
        df[col] = (
            pd.to_numeric(df[col].str.replace(',', ''), errors='coerce')
              .fillna(0)
              .astype(int)
        )
    df["Engagement"] = df["Replies"] + df["Retweets"] + df["Likes"]

    # Content features
    df["Hashtags"]  = df["Tweet"].apply(lambda t: re.findall(r"#\w+", t))
    df["Mentions"]  = df["Tweet"].apply(lambda t: re.findall(r"@\w+", t))
    df["Links"]     = df["Tweet"].apply(lambda t: re.findall(r"https?://\S+", t))
    df["WordCount"] = df["Tweet"].apply(lambda t: len(t.split()))

    # Boolean flags
    df["HasHashtags"] = df["Hashtags"].apply(bool)
    df["HasMentions"] = df["Mentions"].apply(bool)
    df["HasLinks"]    = df["Links"].apply(bool)
    # **Use the scraped media flag** rather than regex
    df["HasMedia"]    = df["HasMedia"].astype(bool)

    return df


def save_user_data(username, df):
    path = os.path.join(DATA_DIR, f"{username}.csv")
    df.to_csv(path, index=False)
    return path


def analyze_user(username, max_tweets=20):
    print(f"\nAnalyzing @{username}...")
    df = fetch_nitter_stats(username, max_tweets)
    if df is None or df.empty:
        print("No data found.")
        return None
    df = process_tweets(df)
    save_user_data(username, df)
    return df


# (print_summary, plot_engagement_heatmap, plot_wordcloud, main() remain unchanged)
# … cut here for brevity …

def print_summary(df, username, follower_count=None):
    print(f"\nDetailed Analysis for @{username}:")
    print("\n1. Tweet Activity")
    print(f"Total tweets analyzed: {len(df)}")

    # Safely format date range
    dt_min = df["Datetime"].min()
    dt_max = df["Datetime"].max()
    if pd.isna(dt_min) or pd.isna(dt_max):
        date_range = "N/A"
    else:
        date_range = f"{dt_min.strftime('%Y-%m-%d')} to {dt_max.strftime('%Y-%m-%d')}"
    print(f"Date range: {date_range}")
    
    print("\n2. Engagement Metrics")
    print(f"Total engagement: {df['Engagement'].sum():,}")
    print(f"Average engagement per tweet: {df['Engagement'].mean():.2f}")
    if follower_count:
        engagement_rate = (df['Engagement'].mean() / follower_count) * 100
        print(f"Average engagement rate: {engagement_rate:.2f}%")
    
    print("\n3. Content Analysis")
    print(f"Tweets with hashtags: {df['HasHashtags'].mean()*100:.1f}%")
    print(f"Tweets with mentions: {df['HasMentions'].mean()*100:.1f}%")
    print(f"Tweets with links: {df['HasLinks'].mean()*100:.1f}%")
    print(f"Tweets with media: {df['HasMedia'].mean()*100:.1f}%")
    print(f"Average word count: {df['WordCount'].mean():.1f}")
    
    print("\n4. Best Performing Tweets")
    top_engagement = df.nlargest(1, 'Engagement').iloc[0]
    top_likes = df.nlargest(1, 'Likes').iloc[0]
    top_retweets = df.nlargest(1, 'Retweets').iloc[0]
    top_replies = df.nlargest(1, 'Replies').iloc[0]
    
    print("\nMost Engaging Tweet:")
    print(f"[{top_engagement['Date']}] {top_engagement['Tweet']}")
    print(f"Engagement: {top_engagement['Replies']} replies, {top_engagement['Retweets']} retweets, {top_engagement['Likes']} likes")
    
    print("\n5. Best Times to Post")
    by_day = df.groupby('DayOfWeek')['Engagement'].mean().sort_values(ascending=False)
    by_hour = df.groupby('Hour')['Engagement'].mean().sort_values(ascending=False)
    
    print("\nBest days to post:")
    for day, eng in by_day.head(3).items():
        print(f"{day}: {eng:.2f} avg engagement")
    
    print("\nBest hours to post (24h):")
    for hour, eng in by_hour.head(3).items():
        print(f"{int(hour):02d}:00: {eng:.2f} avg engagement")  # Convert hour to int
    
    # Print top hashtags and mentions if they exist
    if df['Hashtags'].explode().any():
        top_hashtags = df['Hashtags'].explode().value_counts().head(5)
        print("\n6. Top Hashtags:")
        for tag, count in top_hashtags.items():
            print(f"{tag}: {count} uses")
    
    if df['Mentions'].explode().any():
        top_mentions = df['Mentions'].explode().value_counts().head(5)
        print("\n7. Top Mentions:")
        for mention, count in top_mentions.items():
            print(f"{mention}: {count} mentions")

def plot_engagement_heatmap(df, username):
    if df.empty or len(df) < 2:
        print("Not enough data for heatmap visualization")
        return
        
    pivot = df.pivot_table(
        index='DayOfWeek', 
        columns='Hour', 
        values='Engagement', 
        aggfunc='mean',
        fill_value=0
    )
    
    # Ensure we have some non-zero values before plotting
    if pivot.sum().sum() == 0:
        print("No engagement data available for heatmap")
        return
        
    plt.figure(figsize=(12,6))
    sns.heatmap(pivot, cmap='YlGnBu', annot=True, fmt='.1f')
    plt.title(f"Engagement Heatmap for @{username}")
    plt.tight_layout()
    path = os.path.join('static', f"{username}_heatmap.png")
    plt.savefig(path)
    plt.close()
    print(f"Saved heatmap: {path}")

def plot_wordcloud(df, username):
    text = ' '.join(df['Tweet'])
    wc = WordCloud(width=800, height=400, background_color='white').generate(text)
    plt.figure(figsize=(10,5))
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')
    plt.title(f"Word Cloud for @{username}")
    path = os.path.join('static', f"{username}_wordcloud.png")
    plt.savefig(path)
    plt.close()
    print(f"Saved word cloud: {path}")

def main():
    if len(sys.argv) > 1:
        usernames = sys.argv[1:]
    else:
        usernames = input("Enter X usernames (comma-separated): ").split(',')
        usernames = [u.strip().lstrip('@') for u in usernames if u.strip()]
    for username in usernames:
        df = analyze_user(username)
        if df is not None and not df.empty:
            print_summary(df, username)
            plot_engagement_heatmap(df, username)
            plot_wordcloud(df, username)

if __name__ == "__main__":
    main()