
from collections import namedtuple
import json
import re
import argparse

parser = argparse.ArgumentParser('Testing transfer rule groups')
parser.add_argument('--debug', '-d', action='store_true', default=False)
args = parser.parse_args()

fp = open('qbcc-ph.json', 'r')
records = json.load(fp)
fp.close()

letters = ['F', 'F', 'D-', 'D', 'D+', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+']
def grade(min_gpa, max_gpa):
  """ Convert numerical gpa range to description of required grade in letter-grade form
        below <letter> (when max < 4.0) (should check min < 0.7)
        <letter> or better (when min is > 0.7) (should check max >= 4.0)
        TODO Report anything that doesn't fit one of those two models
        GPA Letter 3×GPA
        4.3 A+      12.9
        4.0 A       12.0
        3.7 A-      11.1
        3.3 B+       9.9
        3.0 B        9.0
        2.7 B-       8.1
        2.3 C+       6.9
        2.0 C        6.0
        1.7 C-       5.1
        1.3 D+       3.9
        1.0 D        3.0
        0.7 D-       2.1
  """
  if max_gpa >= 4.0:
    letter = letters[int(round(min_gpa * 3))]
    return letter + ' or above'
  letter = letters[int(round(max_gpa * 3))]
  return 'below ' + letter

# The values in one row of the db query
QueryRecord = namedtuple('QueryRecord', """
                          source_course_id priority rule_group
                          min_credits max_credits min_gpa max_gpa
                          source_institution_name
                          source_institution source_discipline source_course_number
                          destination_course_id
                          destination_institution_name
                          destination_institution destination_discipline
                          destination_course_number rule_status""")

# After the user has selected source and destination colleges, and source/destination
# disciplines, there is an array of records, which need to be sorted into rule groups.
# Hypothesis: need only look at source institution, source discipline, rule group, and
# destination institution to establish groups. For each group show courses, group prio
# and gpas.

# Group key: combination of properties that identiy a group
GroupKey =namedtuple('GroupKey',"""
                      source_institution source_discipline rule_group destination_institution
                     """)

# Group record: properties for one course-pair in a group. Some of this information is
# redundant across members of the group, so the issue is to sort out the common properties from the
# redundant properties.
GroupRecord = namedtuple('GroupRecord', """
                          source_course_id source_discipline source_course_number
                          rule_priority min_credits max_credits grade
                          destination_course_id destination_discipline destination_course_number
                          rule_status
                          """)
# Course
Course = namedtuple('Course', 'course_id discipline course_number min_credits max_credits')

html = """
<head>
  <title>Testing Transfer Rule Groups</title>
  <style>
    table {border-collapse: collapse;}
    td, th {border: 1px solid #ccc; padding:0.25em;}
  </style>
</head>
<body>
"""
table = '<table>\n'
groups = dict()
for record in records:
  qr = QueryRecord._make(record)
  key = GroupKey._make((qr.source_institution,
                        qr.source_discipline,
                        qr.rule_group,
                        qr.destination_institution))
  value = GroupRecord._make((qr.source_course_id,
                            qr.source_discipline,
                            qr.source_course_number.strip(),
                            qr.priority,
                            qr.min_credits, qr.max_credits,
                            grade(qr.min_gpa, qr.max_gpa),
                            qr.destination_course_id,
                            qr.destination_discipline,
                            qr.destination_course_number.strip(),
                            qr.rule_status))
  if key in groups.keys():
    groups[key].append(value)
  else:
    groups[key] = [value]

# Need to sort groups by the first source course in the group, not just by source institution
# and source discipline.
if args.debug: print('found {} groups'.format(len(groups)))
for key in groups.keys():
  source_courses = set()
  grade = set()
  destination_courses = set()
  rule_status = set()
  if args.debug: print('{} ['.format(key), end='')
  first = True
  for record in groups[key]:
    if args.debug:
      if not first:
        print(', ', end='')
      first = False
      print(record, end='')

    source_courses.add(Course._make((record.source_course_id,
                                     record.source_discipline,
                                     record.source_course_number,
                                     record.min_credits,
                                     record.max_credits)))
    grade.add(record.grade)
    destination_courses.add(Course._make((record.destination_course_id,
                                          record.destination_discipline,
                                          record.destination_course_number,
                                          record.min_credits,
                                          record.max_credits)))
    rule_status.add(record.rule_status)
  if args.debug: print(']')

  assert len(grade) == 1, "Multiple grade requirements for rule group"
  assert len(rule_status) == 1, "Multiple status values for rule group"

  row_id_str = ''

  source_discipline = key.source_discipline
  for n in source_courses:
    assert (n.discipline == source_discipline), "Mixed disciplines in source course set."
  # Peek at first destination discipline
  destination_course = destination_courses.pop()
  destination_courses.add(destination_course)
  destination_discipline = destination_course.discipline
  for n in destination_courses:
    assert (n.discipline == destination_discipline), "Mixed disciplines in destination course set."
  source_courses_str = '{}-{}'.format(key.source_discipline,
               '/'.join(['<span title="{}">{}</span>'.format(n.course_id, n.course_number)
               for n in sorted(source_courses,
               key=lambda t: float(re.match('\d+\.?\d*', t.course_number).group(0)))]))
  row_id_str = ':'.join(['{}'.format(n.course_id) for n in sorted(source_courses,
               key=lambda t: float(re.match('\d+\.?\d*', t.course_number).group(0)))])
  destination_courses_str = '{}-{}'.format(destination_discipline,
               '/'.join(['<span title="{}">{}</span>'.format(n.course_id, n.course_number)
               for n in sorted(destination_courses,
               key=lambda t: float(re.match('\d+\.?\d*', t.course_number).group(0)))]))
  row_id_str += '-'
  row_id_str += ':'.join(['{}'.format(n.course_id) for n in sorted(destination_courses,
               key=lambda t: float(re.match('\d+\.?\d*', t.course_number).group(0)))])
  row = """ <tr id="{}">
              <td title="{}">{}</td>
              <td>{}</td>
              <td>=></td>
              <td title="{}">{}</td>
              <td>{}</td>
              <td>{}</td>
            </tr>"""\
          .format(row_id_str,
                  qr.source_institution_name,
                  qr.source_institution,
                  source_courses_str,
                  qr.destination_institution_name,
                  qr.destination_institution,
                  destination_courses_str,
                  record.rule_status)
  table += '  {}\n'.format(row)

table += '\n</table>'
html = '{}{}\n</body>'.format(html, table)
with open('rules.html', 'w') as r:
  r.write(html)
