name: Update Open Report Tracker

on:
  schedule:
    # Runs every 30 minutes. Adjust as you like (cron is in UTC).
    - cron: "*/30 * * * *"
  issues:
    types: [opened, closed, reopened, edited, deleted]
  workflow_dispatch: {}  # lets you trigger it manually from the Actions tab

permissions:
  contents: write   # needed so the workflow can commit the updated image
  issues: read      # needed so the script can read issue data

jobs:
  build-tracker:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Build tracker image
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/build_tracker.py

      - name: Commit updated tracker image
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add assets/tracker.svg
          git diff --quiet --cached || git commit -m "Update open report tracker"
          git push
