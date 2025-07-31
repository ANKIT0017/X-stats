from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import pandas as pd
import json
from collections import defaultdict
from datetime import datetime
import numpy as np

app = Flask(__name__)
DATA_DIR = "data"
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)  # Create static folder if it doesn't exist

# Helper to list all users with data
def get_all_users():
    return [f[:-4] for f in os.listdir(DATA_DIR) if f.endswith('.csv')]

def safe_serialize(obj, depth=0):
    """Safely serialize data with depth limit to prevent recursion"""
    if depth > 10:  # Prevent infinite recursion
        return str(obj)
        
    if isinstance(obj, (pd.DataFrame, pd.Series)):
        return obj.to_dict()
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    if isinstance(obj, dict):
        return {k: safe_serialize(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [safe_serialize(x, depth + 1) for x in obj]
    if hasattr(obj, 'isoformat'):  # Handle datetime objects
        return obj.isoformat()
    return obj

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ''
    if request.method == 'POST':
        usernames = request.form.get('usernames', '')
        if usernames:
            usernames = [u.strip().lstrip('@') for u in usernames.split(',')]
            for username in usernames:
                os.system(f'python analytics.py "{username}"')
            if len(usernames) > 1:
                return redirect(url_for('compare_users', usernames=','.join(usernames)))
            return redirect(url_for('user_dashboard', username=usernames[0]))
    users = get_all_users()
    return render_template('index.html', users=users, message=message)

@app.route('/user/<username>')
def user_dashboard(username):
    csv_path = os.path.join(DATA_DIR, f'{username}.csv')
    if not os.path.exists(csv_path):
        return f"No data for @{username}", 404
        
    df = pd.read_csv(csv_path)
    
    # Initialize image paths early
    heatmap = f'{username}_heatmap.png'
    wordcloud = f'{username}_wordcloud.png'
    if not os.path.exists(os.path.join(STATIC_DIR, heatmap)):
        heatmap = None
    if not os.path.exists(os.path.join(STATIC_DIR, wordcloud)):
        wordcloud = None
    
    try:
        # Convert Datetime column to proper datetime
        df['Datetime'] = pd.to_datetime(df['Datetime'], errors='coerce')
        
        # Create a simplified stats structure that won't cause circular references
        basic_stats = {
            'tweet_activity': {
                'total_tweets': len(df),
                'date_range': f"{df['Datetime'].min().strftime('%Y-%m-%d')} to {df['Datetime'].max().strftime('%Y-%m-%d')}" if not df['Datetime'].isna().all() else 'N/A'
            },
            'engagement': {
                'total': int(df['Engagement'].sum()),
                'average': round(float(df['Engagement'].mean()), 2),
                'peak': int(df['Engagement'].max())
            },
            'content_analysis': {
                'hashtags_percentage': round(float(df['HasHashtags'].mean() * 100), 1),
                'mentions_percentage': round(float(df['HasMentions'].mean() * 100), 1),
                'links_percentage': round(float(df['HasLinks'].mean() * 100), 1),
                'media_percentage': round(float(df['HasMedia'].mean() * 100), 1),
                'avg_word_count': round(float(df['WordCount'].mean()), 1)
            }
        }
        
        # Add posting patterns
        day_stats = df.groupby('DayOfWeek')['Engagement'].agg(['mean', 'count']).round(2)
        hour_stats = df.groupby('Hour')['Engagement'].agg(['mean', 'count']).round(2)
        
        # Find best times
        best_day = day_stats['mean'].idxmax() if not day_stats.empty else 'N/A'
        best_hour = hour_stats['mean'].idxmax() if not hour_stats.empty else 0
        
        basic_stats['posting_patterns'] = {
            'optimal_time': f"{best_day} at {int(best_hour):02d}:00" if best_day != 'N/A' else 'N/A',
            'days': day_stats.to_dict('index'),
            'hours': {f"{int(h):02d}:00": stats for h, stats in hour_stats.to_dict('index').items()}
        }
        
        return render_template('user_dashboard.html',
                             username=username,
                             stats=basic_stats,
                             recent_tweets=df.head(10).to_dict('records'),
                             heatmap=heatmap,
                             wordcloud=wordcloud)
                             
    except Exception as e:
        print(f"Error calculating stats: {e}")
        import traceback
        traceback.print_exc()
        
        # Return minimal stats structure
        fallback_stats = {
            'tweet_activity': {'total_tweets': len(df), 'date_range': 'N/A'},
            'engagement': {'total': 0, 'average': 0.0, 'peak': 0},
            'content_analysis': {'hashtags_percentage': 0, 'mentions_percentage': 0,
                               'links_percentage': 0, 'media_percentage': 0, 'avg_word_count': 0},
            'posting_patterns': {'optimal_time': 'N/A', 'days': {}, 'hours': {}}
        }
        
        return render_template('user_dashboard.html',
                             username=username,
                             stats=fallback_stats,
                             recent_tweets=[],
                             heatmap=None,
                             wordcloud=None)

@app.route('/compare/<usernames>')
def compare_users(usernames):
    usernames = usernames.split(',')
    all_stats = {}

    for username in usernames:
        csv_path = os.path.join(DATA_DIR, f'{username}.csv')
        if not os.path.exists(csv_path):
            continue

        df = pd.read_csv(csv_path)
        df['Datetime'] = pd.to_datetime(df['Datetime'], errors='coerce')

        # 1) Tweet activity + date range safely
        dt_min = df['Datetime'].min()
        dt_max = df['Datetime'].max()
        if pd.isna(dt_min) or pd.isna(dt_max):
            date_range = 'N/A'
        else:
            date_range = f"{dt_min.strftime('%Y-%m-%d')} to {dt_max.strftime('%Y-%m-%d')}"

        # 2) Engagement & content
        engagement_total   = int(df['Engagement'].sum())
        engagement_avg     = round(float(df['Engagement'].mean()), 2) if len(df) else 0.0
        engagement_peak    = int(df['Engagement'].max()) if len(df) else 0
        hashtags_pct       = round(float(df['HasHashtags'].mean() * 100), 1) if len(df) else 0.0
        mentions_pct       = round(float(df['HasMentions'].mean() * 100), 1) if len(df) else 0.0
        media_pct          = round(float(df['HasMedia'].mean() * 100), 1) if len(df) else 0.0

        # 3) Posting patterns: guard empty groupbys
        day_means  = df.groupby('DayOfWeek')['Engagement'].mean()
        hour_means = df.groupby('Hour')['Engagement'].mean()
        best_day   = day_means.idxmax() if not day_means.empty else 'N/A'
        best_hour  = int(hour_means.idxmax()) if not hour_means.empty else 0

        all_stats[username] = {
            'tweet_activity': {
                'total_tweets': len(df),
                'date_range': date_range,
            },
            'engagement': {
                'total': engagement_total,
                'average': engagement_avg,
                'peak': engagement_peak,
            },
            'content_analysis': {
                'hashtags_percentage': hashtags_pct,
                'mentions_percentage': mentions_pct,
                'media_percentage': media_pct,
            },
            'posting_patterns': {
                'best_day': best_day,
                'best_hour': best_hour,
            }
        }

    comparison = {
        'engagement_rank': sorted(
            all_stats.items(),
            key=lambda x: x[1]['engagement']['average'],
            reverse=True
        ),
        'activity_rank': sorted(
            all_stats.items(),
            key=lambda x: x[1]['tweet_activity']['total_tweets'],
            reverse=True
        ),
        'media_rank': sorted(
            all_stats.items(),
            key=lambda x: x[1]['content_analysis']['media_percentage'],
            reverse=True
        ),
    }

    return render_template('comparison.html',
                           stats=all_stats,
                           comparison=comparison)
@app.route('/static/<path:filename>')
def static_files(filename):
    if filename.endswith('.css'):
        return send_from_directory('static', filename, mimetype='text/css')
    return send_from_directory(STATIC_DIR, filename)

@app.route('/delete/<username>', methods=['POST'])
def delete_user(username):
    # Delete CSV and images
    for ext in ['.csv', '_heatmap.png', '_wordcloud.png']:
        path = os.path.join(DATA_DIR, f'{username}{ext}')
        if os.path.exists(path):
            os.remove(path)
    return redirect(url_for('index'))

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
