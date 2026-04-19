
import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import yaml

try:
    from supabase import create_client
except ImportError:
    create_client = None


CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

DEFAULT_CONFIG = {
    'fetcher': {
        'backend': 'supabase',
        'posts_file': 'posts.json',
        'last_seen_file': 'last_seen.txt',
        'time_window_hours': 24,
        'supabase': {
            'url': SUPABASE_URL,
            'key': SUPABASE_ANON_KEY,
            'table': 'posts',
            'timestamp_column': 'created_at',
        }
    }
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return DEFAULT_CONFIG
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_iso_datetime(value):
    if isinstance(value, str):
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        return datetime.fromisoformat(value)
    raise ValueError('Invalid timestamp format')


def absolute_path(path):
    return path if os.path.isabs(path) else os.path.join(os.path.dirname(__file__), '..', path)


def load_last_seen_timestamp(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        return parse_iso_datetime(content) if content else None


def save_last_seen_timestamp(path, ts: datetime):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(ts.isoformat())


def resolve_env_placeholder(value):
    if not isinstance(value, str):
        return value

    env_match = re.match(r'^\s*os\.getenv\(["\']([^"\']+)["\']\)\s*$', value)
    if env_match:
        return os.getenv(env_match.group(1))

    if value.startswith('${') and value.endswith('}'):
        return os.getenv(value[2:-1])

    return value


def validate_supabase_url(url):
    parsed = urlparse(url or '')
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise ValueError(f"Invalid Supabase URL: {url}")


def get_supabase_client(cfg):
    if create_client is None:
        raise ImportError('Install supabase: pip install supabase')

    url = resolve_env_placeholder(cfg.get('url'))
    key = resolve_env_placeholder(cfg.get('key'))

    if not url or not key:
        raise ValueError('Missing SUPABASE_URL or SUPABASE_KEY')

    validate_supabase_url(url)
    return create_client(url, key)


def fetch_posts_from_supabase(cfg, last_seen_ts, cutoff):
    client = get_supabase_client(cfg)

    table = cfg.get('table', 'posts')
    timestamp_column = cfg.get('timestamp_column', 'created_at')

    query = client.table(table).select('*')

    effective_cutoff = cutoff
    if last_seen_ts and last_seen_ts > cutoff:
        effective_cutoff = last_seen_ts


    query = query.gt(timestamp_column, effective_cutoff.isoformat())

    response = query.order(timestamp_column, desc=False).execute()

    rows = response.data or []

    result = []
    for row in rows:
        try:
            post_time = parse_iso_datetime(row[timestamp_column])
            if post_time > effective_cutoff:
                result.append(row)
        except Exception:
            continue

    return result



def fetch_posts_from_json(posts_file, last_seen_ts, cutoff, timestamp_column):
    if not os.path.exists(posts_file):
        return []

    with open(posts_file, 'r', encoding='utf-8') as f:
        posts = json.load(f)

    effective_cutoff = cutoff
    if last_seen_ts and last_seen_ts > cutoff:
        effective_cutoff = last_seen_ts

    result = []
    for post in posts:
        try:
            post_time = parse_iso_datetime(post[timestamp_column])
            if post_time > effective_cutoff:
                result.append(post)
        except Exception:
            continue

    return result


def fetch_posts():
    config = load_config()
    fetcher = config.get('fetcher', {})

    backend = fetcher.get('backend', 'supabase')
    posts_file = absolute_path(fetcher.get('posts_file', 'posts.json'))
    last_seen_file = absolute_path(fetcher.get('last_seen_file', 'last_seen.txt'))
    time_window_hours = fetcher.get('time_window_hours', 24)

    supabase_cfg = fetcher.get('supabase', {})
    timestamp_column = supabase_cfg.get('timestamp_column', 'created_at')

    last_seen_ts = load_last_seen_timestamp(last_seen_file)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

    if backend == 'supabase':
        posts = fetch_posts_from_supabase(supabase_cfg, last_seen_ts, cutoff)
    else:
        posts = fetch_posts_from_json(posts_file, last_seen_ts, cutoff, timestamp_column)

    if posts:
        newest_ts = max(parse_iso_datetime(p[timestamp_column]) for p in posts)
        save_last_seen_timestamp(last_seen_file, newest_ts)

    return posts


INSURANCE_KEYWORDS = [
   'סוגי ביטוח','ביטוח חובה','ביטוח צד ג׳','ביטוח מקיף','ביטוח נהג צעיר',
   'ביטוח נהג חדש','ביטוח לפי קילומטראז׳','ביטוח רכב חשמלי','כיסויים ותנאים',
   'כיסוי נזקי תאונה','כיסוי גניבה','כיסוי שריפה','כיסוי נזקי טבע','כיסוי שמשות',
   'כיסוי צד שלישי','רכב חלופי','שירותי גרירה','שירותי דרך','מושגים פיננסיים',
   'פרמיה','השתתפות עצמית','פוליסה','חידוש פוליסה','הנחת העדר תביעות',
   'תמחור ביטוח','סיכון ביטוחי','תביעות ותהליכים','הגשת תביעה','שמאי רכב',
   'הערכת נזק','תיקון רכב','מוסך הסדר','אישור תביעה','דחיית תביעה',
   'פרטי רכב ונהג','סוג רכב','שנת ייצור','היסטוריית תאונות','גיל הנהג',
   'ותק נהיגה','נקודות תעבורה','רישיון נהיגה','טכנולוגיה וחדשנות',
   'ביטוח מבוסס שימוש','טלמטיקה',
   'ניתוח נתוני נהיגה','חיישני רכב','AI בביטוח','זיהוי הונאות'
]


def is_insurance_related(post: dict) -> bool:
    text = f"{post.get('title', '')} {post.get('content', '')}".lower()
    return any(kw in text for kw in INSURANCE_KEYWORDS)


def fetch_insurance_posts() -> list:
    posts = fetch_posts()
    return [p for p in posts if is_insurance_related(p)]


if __name__ == '__main__':
    posts = fetch_insurance_posts()
    print(f"Fetched {len(posts)} insurance-related posts:")
    for p in posts:
        print(p)