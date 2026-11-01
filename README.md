# InsureEngine

בוט אוטומטי המנטר פורום קהילתי, מאתר פוסטים בנושאי ביטוח (בעברית) ומגיב להם תגובה הנוצרת באמצעות AI בשיטת **RAG** (Retrieval-Augmented Generation) — תשובה המבוססת על מידע רלוונטי שמאוחזר ממסד נתונים סמנטי, ולא רק על "ידע כללי" של המודל.

## 🎯 מה הפרויקט עושה (הפן המוצרי)

בפורומים קהילתיים (למשל פורומי רכב, דיור וכו׳) מתפרסמות הרבה שאלות בנושא ביטוח — ביטוח רכב, ביטוח דירה, תביעות, פרמיות וכו׳. **InsureEngine** רץ ברקע, "קורא" כל פוסט חדש, ומזהה אם הוא רלוונטי לתחום הביטוח. אם כן — הוא:

1. יוצר שאילתת חיפוש סמנטי על בסיס תוכן הפוסט.
2. מאחזר מידע רלוונטי ממאגר ידע (embeddings) ששמור במסד הנתונים.
3. מפעיל מודל שפה (GPT) שמייצר תשובה מקצועית, ברורה ונעימה, המבוססת על המידע שאוחזר.
4. מפרסם את התשובה כתגובה לפוסט המקורי, בשם "משתמש בוט" ייעודי.

התוצאה: משתמשים בפורום מקבלים מענה ראשוני ומושכל לשאלות ביטוח, מבלי שיידרש מענה אנושי לכל שאלה.

## ⚙️ איך זה עובד (זרימת העבודה)

הבוט פועל בלופ אינסופי (Polling), כל 10 שניות:

```
┌─────────────────┐     ┌────────────────────┐     ┌───────────────────┐     ┌──────────────────┐
│  Post Fetcher    │ ──▶ │ Insurance Filter    │ ──▶ │   RAG Engine       │ ──▶ │ Comment Publisher │
│  שולף פוסטים     │     │ מסנן לפי מילות      │     │  embedding + חיפוש │     │ מפרסם תגובה       │
│  חדשים מ-Supabase│     │ מפתח בעברית         │     │  סמנטי + GPT-4     │     │ בחזרה על הפוסט    │
└─────────────────┘     └────────────────────┘     └───────────────────┘     └──────────────────┘
```

1. **Post Fetcher** (`insure_engine/post_fetcher.py`) — שולף מ-Supabase (או מקובץ JSON מקומי, בהתאם לקונפיגורציה) פוסטים חדשים שפורסמו מאז הריצה האחרונה (או בחלון הזמן המוגדר), ושומר את חותמת הזמן האחרונה שנקראה בקובץ `last_seen.txt`, כדי שלא לעבד פוסט פעמיים.
2. **Insurance Filter** — מתוך הפוסטים שנשלפו, נבחרים רק אלו שמכילים אחת ממגוון מילות מפתח בעברית בתחום הביטוח (כגון "ביטוח חובה", "פוליסה", "תביעה", "השתתפות עצמית", "ביטוח מבוסס שימוש" ועוד).
3. **RAG Engine** (`insure_engine/supabase_rag.py`) —
   - מייצר embedding לשאלה באמצעות מודל ה-embeddings של OpenAI (`text-embedding-3-small`).
   - מבצע חיפוש דמיון וקטורי (cosine similarity) מול טבלת ה-embeddings בפוסטגרס/Supabase (pgvector) באמצעות פונקציית RPC בשם `match_embeddings_cosine`.
   - בונה פרומפט שמשלב את ההקשר שאוחזר עם שאלת המשתמש.
   - שולח את הפרומפט למודל GPT-4 עם הנחיות מערכת (System Prompt) שמגדירות טון ענייני ונעים, תשובה מבוססת-הקשר, ותוספת לינקים למידע נוסף.
4. **Comment Publisher** (`insure_engine/comments.py`) — מפרסם את התשובה שחזרה מה-RAG כתגובה חדשה בטבלת `comments` ב-Supabase, בשם משתמש הבוט (`BOT_USER_ID`).

כל המחזור מתואם מתוך `main.py`, שמריץ לופ `while True` עם `time.sleep` בין איטרציה לאיטרציה, ורושם לוג (`logging`) על כל שלב ועל חריגות.

## 🧰 הפן הטכנולוגי (Tech Stack)

| רכיב | טכנולוגיה |
|---|---|
| שפת תכנות | Python 3 |
| מסד נתונים | Supabase (Postgres) |
| חיפוש סמנטי | pgvector + פונקציית RPC מותאמת (`match_embeddings_cosine`) |
| מודל Embeddings | OpenAI `text-embedding-3-small` |
| מודל שיחה/ייצור טקסט | OpenAI `gpt-4` |
| ניהול קונפיגורציה | קובץ `.env` (`python-dotenv`) + קובץ `config/config.yaml` אופציונלי (`pyyaml`) |
| פריסה | Render — כ-Background Worker |

## 📁 מבנה הפרויקט

```
InsureEngine/
├── main.py                        # נקודת הכניסה — לופ ה-polling הראשי
├── insure_engine/
│   ├── __init__.py
│   ├── post_fetcher.py            # שליפה וסינון פוסטים (Supabase / JSON מקומי)
│   ├── comments.py                # פרסום תגובות וקריאה ל-RAG
│   └── supabase_rag.py            # embedding, חיפוש סמנטי וייצור תשובה
├── tests/
│   └── __init__.py                # שלד לבדיקות (ריק כרגע)
├── last_seen.txt                  # חותמת הזמן של הפוסט האחרון שעובד
├── requirements.txt                # רשימת תלויות (ראו הערה למטה)
├── .gitignore
└── README.md
```

> **הערה:** `requirements.txt` כרגע הוא קובץ שלד בלבד וללא תלויות רשומות בפועל. בהתאם לייבואים בקוד, התלויות הנדרשות להרצה הן לפחות: `supabase`, `openai`, `python-dotenv`, `pyyaml`. מומלץ להוסיף אותן לקובץ (ראו שלב ההתקנה למטה).

## 🚀 התקנה והרצה

### דרישות מוקדמות

- Python 3.10+‎
- פרויקט Supabase פעיל, עם:
  - טבלת `posts` (עם עמודות `id`, `title`, `content`, `created_at` לפחות)
  - טבלת `comments` (עם עמודות `id`, `post_id`, `user_id`, `content`, `created_at`)
  - טבלת embeddings עם תמיכת `pgvector` ופונקציית RPC בשם `match_embeddings_cosine`
- מפתח API של OpenAI

### שלבי התקנה

1. שכפול הריפו:
   ```bash
   git clone https://github.com/efrat-stinberg/InsureEngine.git
   cd InsureEngine
   ```

2. התקנת תלויות (יש להשלים את `requirements.txt` עם החבילות הנדרשות, או להתקין ישירות):
   ```bash
   pip install supabase openai python-dotenv pyyaml
   ```

3. יצירת קובץ `.env` בשורש הפרויקט עם המשתנים הבאים:
   ```env
   SUPABASE_URL=
   SUPABASE_ANON_KEY=
   SUPABASE_SERVICE_ROLE_KEY=
   SUPABASE_KEY=
   OPENAI_API_KEY=
   BOT_USER_ID=
   ```
   - `SUPABASE_URL` / `SUPABASE_ANON_KEY` — נדרשים לשליפת הפוסטים (`post_fetcher.py`).
   - `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` — נדרשים לפרסום התגובות (`comments.py`), שכן נדרשת הרשאת כתיבה.
   - `SUPABASE_URL` / `SUPABASE_KEY` — נדרשים לרכיב ה-RAG (`supabase_rag.py`) לצורך ביצוע ה-RPC של החיפוש הסמנטי.
   - `OPENAI_API_KEY` — מפתח ה-API של OpenAI, לייצור embeddings ולייצור התשובות.
   - `BOT_USER_ID` — ה-UUID של משתמש הבוט בטבלת המשתמשים, שבשמו יפורסמו התגובות.

4. (אופציונלי) יצירת `config/config.yaml` לשינוי התנהגות ברירת המחדל של ה-Fetcher (למשל מעבר ממקור Supabase למקור קובץ JSON מקומי, או שינוי חלון הזמן לבדיקת פוסטים חדשים). ללא קובץ כזה, נטענת קונפיגורציית ברירת מחדל מתוך `post_fetcher.py`.

5. הרצת הבוט:
   ```bash
   python main.py
   ```

   הבוט יתחיל לרוץ בלופ, ייבדק פוסטים חדשים כל 10 שניות (`POLL_INTERVAL` ב-`main.py`), ויפרסם תגובות לפוסטים רלוונטיים בתחום הביטוח.

## ☁️ פריסה (Deployment)

הפרויקט מתאים לפריסה כ-**Background Worker** בשירות [Render](https://render.com/):

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python main.py`
- יש להגדיר את כל משתני הסביבה שפורטו לעיל בהגדרות ה-Environment של השירות ב-Render.

## 🧪 בדיקות

תיקיית `tests/` קיימת כשלד לבדיקות (`__init__.py` בלבד, ללא בדיקות בפועל עדיין). מומלץ להוסיף בדיקות יחידה לרכיבי הסינון (`is_insurance_related`), טעינת/שמירת חותמת הזמן (`load_last_seen_timestamp`, `save_last_seen_timestamp`), ובניית פרומפט ההקשר (`build_context_prompt`).

## 📌 נקודות לתשומת לב

- שמות משתני הסביבה של מפתחות Supabase אינם עקביים בין הקבצים (`SUPABASE_ANON_KEY`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`) — לכל רכיב בפרויקט יש משתנה שונה שהוא קורא, כך שיש להגדיר את כולם ב-`.env`.
- `requirements.txt` אינו מכיל תלויות בפועל כיום — יש להשלים אותו בהתאם לחבילות הנדרשות (ראו סעיף ההתקנה).
- קובץ הקונפיגורציה `config/config.yaml` הנזכר בקוד (`post_fetcher.py`) אינו קיים כברירת מחדל בריפו; הפרויקט פועל ללא בעיה גם בלעדיו, תוך שימוש בקונפיגורציית ברירת המחדל המוגדרת בקוד.
