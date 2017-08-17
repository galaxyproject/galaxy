#!/bin/bash
export COLUMN_LIMIT=160
yapf -p -i -r --style='{based_on_style: pep8, column_limit: 140}' lib
