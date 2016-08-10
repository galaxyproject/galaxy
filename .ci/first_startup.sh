#!/bin/bash
TRIES=120
URL=http://localhost:8080
echo "Testing for correct startup:"
bash run.sh --daemon && \
while [[ $i -le $TRIES ]]
do
    curl "$URL" && EXIT_CODE=0 && break
    sleep 1
    EXIT_CODE=1
    ((i = i + 1))
done
echo "exit code:$EXIT_CODE, showing startup log:"
cat paster.log
exit $EXIT_CODE
