#!/bin/bash
# Hard wall-time stop for MY bf16 app ap-yw0xJBjNgTIQhG62v8Ck82 (1 H100, timeout 1200s).
cd /Users/sarosh/programming/research-sprint-1023
NOW=$(date +%s); WAIT=$(( 1792926000 - NOW )); [ $WAIT -gt 0 ] && sleep $WAIT
echo "$(date) watchdog: stopping ap-yw0xJBjNgTIQhG62v8Ck82" >> explore/weight_amplify/logs/watchdog.log
pkill -f "modal run modal_amplify.py --stage bf16" 2>/dev/null
modal app stop ap-yw0xJBjNgTIQhG62v8Ck82 >> explore/weight_amplify/logs/watchdog.log 2>&1
