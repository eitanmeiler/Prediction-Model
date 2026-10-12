#!/bin/bash
# Copies the tracker to a runtime folder outside ~/Desktop (macOS blocks launchd jobs from Desktop)
# and links the repo's data/live to it. Re-run after editing track_wiki.py or watchlist.json.
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
RT="$HOME/Library/Application Support/PredictionModel"
mkdir -p "$RT/tracker" "$RT/data/live"
cp "$REPO/tracker/track_wiki.py" "$REPO/tracker/watchlist.json" "$RT/tracker/"
if [ -d "$REPO/data/live" ] && [ ! -L "$REPO/data/live" ]; then
  cp -n "$REPO/data/live/"* "$RT/data/live/" 2>/dev/null || true
  rm -rf "$REPO/data/live"
fi
[ -L "$REPO/data/live" ] || ln -s "$RT/data/live" "$REPO/data/live"
PL="$HOME/Library/LaunchAgents/com.predictionmodel.tracker.plist"
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:1 $RT/tracker/track_wiki.py" "$PL"
/usr/libexec/PlistBuddy -c "Set :StandardOutPath $RT/data/live/launchd.out" "$PL"
/usr/libexec/PlistBuddy -c "Set :StandardErrorPath $RT/data/live/launchd.err" "$PL"
launchctl bootout gui/$(id -u)/com.predictionmodel.tracker 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$PL"
echo "installed -> $RT"
