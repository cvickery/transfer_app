#! /usr/local/bin/bash

# Extract requirement_text from the db.
# Get the institution from the environment, but get the block_value from the command line.

institution=$INSTITUTION
[[ -z $institution ]] && institution='qns'

value=CSCI-BA
if [[ $# -gt 0 ]]
then value=$1
fi

psql cuny_programs -Xqtc "select requirement_text \
from requirement_blocks
where institution = '$institution'
and block_value = '$value'
and period_stop = '99999999'" | sed s/\ *+$// |sed s/\\\\r//
