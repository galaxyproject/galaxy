#! /bin/bash
if [ ! -d galaxy ];
then
    git clone https://github.com/galaxyproject/galaxy.git galaxy
fi
cd galaxy
git pull
cd ..

if [ ! -d tools-iuc ];
then
    git clone https://github.com/galaxyproject/tools-iuc.git tools-iuc
fi
cd tools-iuc
git pull
cd ..

count=`wc -l tool_files.list | cut -f1 -d' '`
echo "1..$count"
count=0
while read p; do
    count=$((count+1))
    path=$p

    result=`planemo normalize --expand_macros "$path" | xmllint --nowarning --noout --schema galaxy.xsd - 2> err.tmp`
    if [ $? -eq 0 ]
    then
        echo "ok $count $url";
    else
        echo "not ok $count $path";
        cat err.tmp  | sed 's/^/    /'
    fi
done <tool_files.list
rm err.tmp
