exclude=$(sed -e 's|^|./|' -e 's|/$||' .ci/flake8_ignorelist.txt | paste -s -d ',' - )
autopep8 -i -r --exclude $exclude --select E11,E101,E127,E201,E202,E22,E301,E302,E303,E304,E306,E711,W291,W292,W293,W391 ./lib/ ./test/
