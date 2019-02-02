#!/usr/bin/env bash

export PATH=$PATH:$(dirname $0)

input=$1
min_window=$2
max_window=$3
false_num=$4
output=$5

pass "$input" "$min_window" "$max_window" "$false_num" "$output" >/dev/null
sed -i -e 's/\t\t*/\t/g' "$output"

