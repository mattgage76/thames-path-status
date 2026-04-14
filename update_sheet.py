"""
Thames Path Status — weekly auto-updater
Calls the Claude API with web search to research current incidents,
then writes the results into PathStatus.xlsx.
"""

import os
import json
import time
import textwrap
from datetime import date
import anthropic
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# ── Config ────────────────────────────────────────────────────────────────────

XLSX_PATH = "PathStatus.xlsx"
LOG_PATH  = "update_log.txt"
TODAY     = date.today().isoformat()

# Sources to search
SEARCH_QUERIES = [
    "Thames Path closures diversions 2026",
    "Thames Path National Trail incidents alerts site:nationaltrail.co.uk",
    "Thames Path route alerts site:walkthethames.co.uk",
    "Thames Path status Environment Agency bridge closures 2026",
]

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
    You are an assistant that tracks live closures, diversions, construction works
    and incidents along the Thames Path National Trail in England.

    When asked, search the web thoroughly using the web_search tool, then return
    a JSON array — and ONLY a JSON array, no markdown fences, no preamble.

    Each element must have exactly these fields:
      type          : one of: closure, construction, incident, info
      type2         : one of: diversion, intermittent, open, closure, or null
      title         : short descriptive title (max 80 chars)
      description   : full details including diversion instructions (max 600 chars)
      mile          : float (miles from source) or null
      status        : human-readable status string
      date          : ISO date the issue started (YYYY-MM-DD) or null
      last_verified : today's ISO date
      source        : URL of primary source or null
      lat           : float latitude or null
      lon           : float longitude or null

    Include ALL currently active issues — do not omit any known long-term closures
    even if unchanged. Mark anything that has recently reopened with type=info,
    type2=open, and status=Open (re-opened).

    Today's date is {today}.
""").strip()

USER_PROMPT = textwrap.dedent("""
    Please search the web for ALL current Thames Path closures, diversions,
    construction works and incidents as of today ({today}).

    Search these sources:
    - https://www.nationaltrail.co.uk/en_GB/trails/thames-path/
    - https://walkthethames.co.uk/thames-path-status/
    - https://engageenvironmentagency.uk.engagementhq.com/thames-area-assets
    - https://www.gov.uk/guidance/river-thames-restrictions-and-closures

    Known long-term issues to verify/update (confirm still active or mark reopened):
    - Osney Bridge / Botley Road construction diversion (Oxford, mile ~53.8)
    - Marsh Lock footbridge closure (Henley, mile ~105.1)
    - Sandford Footbridge closure (mile ~57.0)
    - Abingdon Weir walkway intermittent closure (mile ~62.0)
    - Temple Footbridge closure and Marlow Bridge weekend closures (mile ~108.5)
    - Runnymede Bridge 142 closure (mile ~136.5)
    - Bell Weir / Runnymede Pleasure Grounds diversion (mile ~136.2)
    - Streatley–Goring eroding towpath diversion (mile ~81.5)
    - Penton Hook Island closure (mile ~135.6)
    - Ten Foot Bridge closure near Faringdon (mile ~34.0)
    - Brentford Grand Union Canal disruption (mile ~154.0)

    Also search for any NEW incidents or diversions opened in the last 7 days.

    Return ONLY a valid JSON array.
""").strip()

# ── Claude API call with web search ──────────────────────────────────────────

def fetch_updates_from_claude():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("Calling Claude API with web search...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=SYSTEM_PROMPT.format(today=TODAY),
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": USER_PROMPT.format(today=TODAY)}],
    )

    # Collect all text blocks (may follow tool_use/tool_result turns)
    # If the model used tools, we need to continue the conversation
    messages = [{"role": "user", "content": USER_PROMPT.format(today=TODAY)}]

    while response.stop_reason == "tool_use":
        # Build assistant message from response
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        # Build tool results
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Search completed.",  # Claude handles this internally
                })

        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM_PROMPT.format(today=TODAY),
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )
        time.sleep(1)

    # Extract JSON from the final text response
    full_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            full_text += block.text

    # Strip any accidental markdown fences
    clean = full_text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]
        clean = clean.rsplit("```", 1)[0]

    return json.loads(clean.strip())


# ── Write to Excel ────────────────────────────────────────────────────────────

HEADERS = ["Type","Type2","Title","Description","Mile","Status",
           "Date","Last Verified","Source","Lat","Lon"]

COL_WIDTHS = [14, 14, 45, 80, 6, 28, 12, 14, 60, 12, 12]

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(name="Arial", size=10, bold=True, color="FFFFFF")
DATA_FONT   = Font(name="Arial", size=10)
WRAP_TOP    = Alignment(wrap_text=True, vertical="top")
CENTER      = Alignment(horizontal="center", vertical="center")


def write_xlsx(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "PathStatus"

    # Header row
    for c, h in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font   = HEADER_FONT
        cell.fill   = HEADER_FILL
        cell.alignment = CENTER
    ws.row_dimensions[1].height = 20

    # Data rows
    for r, row in enumerate(rows, 2):
        vals = [
            row.get("type"),
            row.get("type2"),
            row.get("title"),
            row.get("description"),
            row.get("mile"),
            row.get("status"),
            row.get("date"),
            row.get("last_verified", TODAY),
            row.get("source"),
            row.get("lat"),
            row.get("lon"),
        ]
        for c, val in enumerate(vals, 1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.font      = DATA_FONT
            cell.alignment = WRAP_TOP
        ws.row_dimensions[r].height = 60

    # Column widths
    for c, w in enumerate(COL_WIDTHS, 1):
        ws.column_dimensions[ws.cell(1, c).column_letter].width = w

    # Freeze header
    ws.freeze_panes = "A2"

    wb.save(XLSX_PATH)
    print(f"Saved {len(rows)} rows to {XLSX_PATH}")


# ── Log ───────────────────────────────────────────────────────────────────────

def write_log(rows, error=None):
    with open(LOG_PATH, "w") as f:
        f.write(f"Thames Path Status Update Log\n")
        f.write(f"Run date : {TODAY}\n")
        if error:
            f.write(f"ERROR    : {error}\n")
        else:
            f.write(f"Rows     : {len(rows)}\n")
            f.write(f"Status   : OK\n\n")
            for row in rows:
                f.write(f"  [{row.get('status','?')}] {row.get('title','?')}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        rows = fetch_updates_from_claude()
        print(f"Received {len(rows)} rows from Claude")
        write_xlsx(rows)
        write_log(rows)
        print("Update complete.")
    except Exception as e:
        print(f"ERROR: {e}")
        write_log([], error=str(e))
        raise
