import os, json, time, hashlib, requests, feedparser, re
from datetime import datetime, timezone

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
TWITTER_USERNAME = "GUNDAM_GCG_JP"
RSS_SOURCES = [
    f"https://nitter.poast.org/{TWITTER_USERNAME}/rss",
    f"https://nitter.privacydev.net/{TWITTER_USERNAME}/rss",
    f"https://nitter.lunar.icu/{TWITTER_USERNAME}/rss",
]
SENT_CACHE_FILE = "sent_tweets_cache.json"

def load_cache():
    if os.path.exists(SENT_CACHE_FILE):
        with open(SENT_CACHE_FILE) as f:
            return set(json.load(f).get("sent_ids", []))
    return set()

def save_cache(sent_ids):
    with open(SENT_CACHE_FILE, "w") as f:
        json.dump({"sent_ids": list(sent_ids)[-500:]}, f)

def fetch_tweets():
    headers = {"User-Agent": "Mozilla/5.0"}
    for url in RSS_SOURCES:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.content)
            if not feed.entries:
                continue
            tweets = []
            for e in feed.entries[:10]:
                tid = hashlib.md5(e.get("id", e.link).encode()).hexdigest()
                link = re.sub(r'https?://[^/]+', 'https://x.com', e.get("link", ""))
                tweets.append({"id": tid, "summary": e.get("summary", e.get("title", "")), "link": link})
            print(f"✅ ดึงได้ {len(tweets)} ทวีตจาก {url}")
            return tweets
        except Exception as ex:
            print(f"❌ {url} → {ex}")
    return []

def clean_html(text):
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.replace('&amp;','&').replace('&lt;','<').replace('&gt;','>').strip()

def send_to_discord(tweet):
    text = clean_html(tweet["summary"])
    if len(text) > 1000:
        text = text[:997] + "..."
    payload = {
        "username": "Gundam GCG Updates",
        "embeds": [{
            "author": {"name": f"@{TWITTER_USERNAME}", "url": f"https://x.com/{TWITTER_USERNAME}"},
            "description": text,
            "url": tweet["link"],
            "color": 0x1DA1F2,
            "footer": {"text": "🤖 Gundam GCG Bot"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    }
    r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    return r.status_code in (200, 204)

sent_ids = load_cache()
tweets = fetch_tweets()
new_count = 0
for tweet in reversed(tweets):
    if tweet["id"] not in sent_ids:
        if send_to_discord(tweet):
            sent_ids.add(tweet["id"])
            new_count += 1
            time.sleep(1)
save_cache(sent_ids)
print(f"✅ ส่งทวีตใหม่ {new_count} รายการ")
