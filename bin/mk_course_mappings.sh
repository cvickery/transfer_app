#! /usr/local/bin/bash

export PROJS_DIR=/Users/vickery/Projects

psql cuny_curriculum < $PROJS_DIR/transfer_app/bin/mk_course_mappings.sql
