#!/bin/bash
# Hard stop for MY diag app ap-UVBcAOCoo8aIUVKrEqWXK7 (CPU merge + 1 H100 diag), at 04:16 PDT.
cd /Users/sarosh/programming/research-sprint-1023
NOW=$(date +%s); WAIT=$(( 1792926960 - NOW )); [ $WAIT -gt 0 ] && sleep $WAIT
echo "$(date) watchdog: stopping ap-UVBcAOCoo8aIUVKrEqWXK7" >> studies/diagnostics/weight_amplify/logs/watchdog.log
pkill -f "modal run modal_amplify.py --stage diag" 2>/dev/null
modal app stop ap-UVBcAOCoo8aIUVKrEqWXK7 >> studies/diagnostics/weight_amplify/logs/watchdog.log 2>&1
