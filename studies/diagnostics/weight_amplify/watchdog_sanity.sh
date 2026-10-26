#!/bin/bash
# Hard wall-time watchdog for MY sanity app ap-7IilsIkoP5lfak7i9FKoav (HF greedy, one H100, timeout 900s).
cd /Users/sarosh/programming/research-sprint-1023
NOW=$(date +%s); WAIT=$(( 1792926480 - NOW )); [ $WAIT -gt 0 ] && sleep $WAIT
echo "$(date) watchdog: stopping ap-7IilsIkoP5lfak7i9FKoav" >> studies/diagnostics/weight_amplify/logs/watchdog.log
pkill -f "modal run studies/diagnostics/weight_amplify/modal_amplify.py --stage sanity" 2>/dev/null
modal app stop ap-7IilsIkoP5lfak7i9FKoav >> studies/diagnostics/weight_amplify/logs/watchdog.log 2>&1
