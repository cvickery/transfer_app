#! /usr/local/bin/python3
""" Filter the access log to get rid of health checks and to columnificizate fields of interst.
"""
import os
import re
import sys

lookups = dict()
with open('./access.csv', 'w') as csv_file:
  csv_file.write('Address, Lookup, Date, Query, Referer\n')
exit()

# Ignore this; it's not working and not worth fixing right now!

#  for line in sys.stdin:
#    if line.startswith('149.4.99.6'):
#      # the date is enclosed in square brackets
#      matches = re.search(r'\[(.*)\]', line)
#      date_str = matches.group(1)
#      tokens = line.split()
#      if tokens[1] not in lookups.keys():
#        stream = os.popen(f'dig +noall +answer -x {tokens[1]}')
#        answer = stream.read().strip()
#        matches = re.search(r'.*PTR(.*)', answer)
#        try:
#          lookups[tokens[1]] = matches.group(1).strip()
#        except AttributeError as ae:
#          lookups[tokens[1]] = answer
#      lookup_str = lookups[tokens[1]]
#      csv_file.write(f'{tokens[1]}, {lookup_str}, {date_str}, {tokens[5]},{tokens[9]}\n')
