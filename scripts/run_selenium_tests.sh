#!/bin/sh

if [ ! -f selenium-server.jar ]; then
    echo "Need to download selenium-server.jar from:"
    echo "http://nexus.openqa.org/content/repositories/snapshots/org/seleniumhq/selenium/server/selenium-server/1.0-SNAPSHOT/selenium-server-1.0-20090319.053109-107-standalone.jar"
fi

java -jar selenium-server.jar -htmlSuite "*firefox" "http://localhost:8080" ./test/selenium/workflow/Suite.html ./selenium_results.html
