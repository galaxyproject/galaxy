echo "Testing for correct startup:"
bash run.sh --daemon && sleep 30s && curl -I localhost:8080
EXIT_CODE=$?
echo "exit code:$EXIT_CODE, showing startup log:"
cat paster.log
exit $EXIT_CODE
