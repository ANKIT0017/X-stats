# 📊 X-Stats — Twitter/X Profile Analytics Dashboard

**X-Stats** is a web dashboard built with Flask that allows you to analyze and compare up to **three Twitter/X profiles** at a time. It extracts key metrics from user tweets and visualizes insights like:

- 📈 Engagement trends  
- 🕒 Best times to post  
- 📸 Media usage  
- 🔥 Hashtag & mention frequency  
- 🌐 Wordclouds and heatmaps  

---

## 🚀 Features

✅ Analyze individual Twitter/X profiles  
✅ Compare **up to 3 users** side-by-side  
✅ Automatically generates:
- Engagement stats (total, average, peak)  
- Content analysis (hashtags, mentions, media, links)  
- Posting patterns (best day and time)  
- Recent tweets with metadata  
- Heatmap and wordcloud visualizations  

✅ Intuitive web dashboard interface  
✅ File cleanup system to manage memory  
✅ Built with Flask, Pandas, Matplotlib, and more  

---

## 📂 Folder Structure

X-Stats/
│
├── data/ # CSVs for each analyzed user
├── static/ # Wordclouds, heatmaps
├── templates/ # HTML pages
├── analytics.py # Tweet fetching & preprocessing
├── web_dashboard.py # Main Flask app
├── requirements.txt # Dependencies
└── README.md

---

---

## 🛠️ How to Run Locally

1. **Clone the repo**

    ```bash
    git clone https://github.com/ANKIT0017/X-stats.git
    cd X-stats
    ```

2. **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

3. **Run the web dashboard**

    ```bash
    python web_dashboard.py
    ```

4. **Open in your browser**

    ```
    http://127.0.0.1:5000
    ```

---

## 🌐 Live Demo

🔗 Hosted on: [https://x-stats.onrender.com](https://x-stats.onrender.com)

> ⚠️ Note: This app may hit memory limits on free-tier Render if multiple users are analyzed concurrently. Consider using Railway or Fly.io for production.

---

## 🤝 Contribute

We welcome all contributions!

- Found a bug? Open an issue.  
- Have a feature idea? Let’s hear it.  
- Want to improve the visuals or backend? Go for it!  

**Feel free to fork, star, or submit pull requests.**

---

## 📄 License

MIT License

---

> Built with ❤️ to make sense of Twitter/X analytics.
