#!/bin/bash
# Hard wall-time watchdog for MY app only (dolos-weight-amplify, ap-XW8cyygyoCbRlKMmyVZbbS).
cd /Users/sarosh/programming/research-sprint-1023
NOW=$(date +%s); WAIT=$(( 1792926000 - NOW )); [ $WAIT -gt 0 ] && sleep $WAIT
echo "$(date) watchdog firing: stopping ap-XW8cyygyoCbRlKMmyVZbbS" >> studies/diagnostics/weight_amplify/logs/watchdog.log
pkill -f "modal run studies/diagnostics/weight_amplify/modal_amplify.py" 2>/dev/null
modal app stop ap-XW8cyygyoCbRlKMmyVZbbS >> studies/diagnostics/weight_amplify/logs/watchdog.log 2>&1
echo "$(date) stop issued" >> studies/diagnostics/weight_amplify/logs/watchdog.log
