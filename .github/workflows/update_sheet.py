name: Update Thames Path Status Sheet

on:
  schedule:
    - cron: '0 7 * * 1'
  workflow_dispatch:

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

jobs:
  update:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run updater
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python update_sheet.py

      - name: Show log on failure
        if: failure()
        run: cat update_log.txt || echo "No log file found"

      - name: Commit updated sheet
        run: |
          git config user.name  "Thames Path Bot"
          git config user.email "bot@users.noreply.github.com"
          git add PathStatus.xlsx PathStatus.csv update_log.txt
          git diff --cached --quiet || git commit -m "Auto-update: Thames Path status $(date +'%Y-%m-%d')"
          git push
