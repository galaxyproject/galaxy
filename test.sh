#! /bin/bash
count=`wc -l test.urls  | cut -f1 -d' '`
root_url="https://bitbucket.org/galaxy/galaxy-central/raw/c3eefbdaaa1ab242a1c81b65482ef2fbe943a390/"
echo "1..$count"
count=0
while read p; do
    count=$((count+1))
    url="$root_url""$p"
    result=`curl -ksL "$url" | xmllint --nowarning --noout --schema galaxy.xsd - 2> err.tmp`
    if [ $? -eq 0 ]
    then
        echo "ok $count $url";
    else
        echo "not ok $count $url";
        cat err.tmp  | sed 's/^/    /'
    fi
done <test.urls
rm err.tmp
