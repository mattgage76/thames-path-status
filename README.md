# Thames Path Status — Weekly Auto-Updater

Automatically searches for Thames Path closures, diversions and incidents every Monday morning using Claude AI with web search, then updates `PathStatus.xlsx` and commits it back to this repo.

---

## Setup (one-time, ~20 minutes)

### 1. Create a GitHub repository

- Go to https://github.com/new
- Name it `thames-path-status` (or anything you like)
- Set it to **Public** (needed so your Google Sheets CSV URL works publicly) or Private
- Click **Create repository**

### 2. Upload these files

Upload all files from this folder into the root of your new repo:
- `update_sheet.py`
- `requirements.txt`
- `.github/workflows/update-sheet.yml`
- `PathStatus.xlsx` (your current sheet — the script will overwrite it each week)

### 3. Add your Anthropic API key as a secret

- In your repo, go to **Settings → Secrets and variables → Actions**
- Click **New repository secret**
- Name: `ANTHROPIC_API_KEY`
- Value: your Anthropic API key (get one free at https://console.anthropic.com)
- Click **Add secret**

### 4. Enable Actions

- Go to the **Actions** tab in your repo
- If prompted, click **I understand my workflows, go ahead and enable them**

### 5. Test it manually

- Go to **Actions → Update Thames Path Status Sheet**
- Click **Run workflow → Run workflow**
- Watch the logs — it should complete in ~2 minutes and commit an updated `PathStatus.xlsx`

---

## Connecting to your website

Once the sheet is in your repo, get the raw CSV URL:

1. Open `PathStatus.xlsx` in your repo on GitHub
2. Click the **Raw** button — copy that URL
3. The URL will look like:
   `https://raw.githubusercontent.com/YOURNAME/thames-path-status/main/PathStatus.xlsx`

**However** — your map uses a Google Sheets CSV URL. The easiest way to keep that working is:

**Option A — Keep using Google Sheets:**
After each GitHub run, manually copy the new data into your Google Sheet.
(Defeats the automation a bit, but keeps your existing map code unchanged.)

**Option B — Switch to GitHub CSV:**
- In your repo, also save the data as `PathStatus.csv` (add one line to the script)
- Update your map's `CSV_URL` to point to the raw GitHub CSV URL
- This is fully automatic — no Google Sheets needed

To enable Option B, add this line near the end of `update_sheet.py` (after `write_xlsx`):

```python
import csv
with open("PathStatus.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Type","Type2","Title","Description",
                                            "Mile","Status","Date","Last Verified",
                                            "Source","Lat","Lon"])
    writer.writeheader()
    for row in rows:
        writer.writerow({
            "Type": row.get("type",""), "Type2": row.get("type2",""),
            "Title": row.get("title",""), "Description": row.get("description",""),
            "Mile": row.get("mile",""), "Status": row.get("status",""),
            "Date": row.get("date",""), "Last Verified": row.get("last_verified",""),
            "Source": row.get("source",""), "Lat": row.get("lat",""),
            "Lon": row.get("lon",""),
        })
```

Then change your map's CSV_URL to:
```
https://raw.githubusercontent.com/YOURNAME/thames-path-status/main/PathStatus.csv
```

---

## Schedule

The workflow runs every **Monday at 7am UTC** (8am BST in summer).

To change the schedule, edit `.github/workflows/update-sheet.yml` and change the cron line:
```yaml
- cron: '0 7 * * 1'   # min hour day month weekday (1=Monday)
```

---

## Cost

- GitHub Actions: **free** (2,000 minutes/month on free tier; this uses ~2 min/week)
- Anthropic API: Claude Sonnet with web search costs roughly **$0.02–0.05 per run**
  (~$2–3/year)
