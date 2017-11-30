
from collections import namedtuple
import json
import re
import argparse

from evaluations import status_string, rule_history
DEBUG = False

letters = ['F', 'F', 'D-', 'D', 'D+', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+']

# _grade()
# -------------------------------------------------------------------------------------------------
def _grade(min_gpa, max_gpa):
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

# format_groups()
# -------------------------------------------------------------------------------------------------
def format_groups(groups, session):
  """ Generate HTML table with information about each rule group.
  """
  institution_names = session['institution_names']
  table = """
    <table id="rules-table">
      <thead>
        <tr>
        <th>Sending</th><th>Courses</th><th></th><th>Receiving</th><th>Courses</th><th>Evaluation</th>
        </tr>
      </thead>
      <tbody>
      """
  for group in groups:
    # The id for the row will be a colon-separated list of course_ids, with source and destinations
    # separated by a hyphen
    row_id_str = ''

    # Build the source part of the rule group
    source_credits = 0.0
    grade = ''
    discipline = ''
    catalog_number = ''
    grade = ''
    source_course_list = ''
    for course in group.source_courses:

      course_grade = _grade(course.min_gpa, course.max_gpa)

      if course_grade != grade:
        if grade != '': source_course_list = source_course_list.strip('/') + '; '
        grade = course_grade
        source_course_list = source_course_list.strip('/') + ' {} in '.format(grade)

      if discipline != course.discipline:
        if discipline != '': source_course_list = source_course_list.strip('/') +'; '
        discipline = course.discipline
        discipline_str = '<span title="{}">{}</span>'.format(course.discipline_name,
                                                             course.discipline)
        source_course_list = source_course_list.strip('/') + discipline_str + '-'
        print(':{}:'.format(source_course_list))
      if catalog_number != course.catalog_number:
        catalog_number = course.catalog_number
        source_course_list += '<span title="course id: {}">{}</span>/'.format(course.course_id,
                                                                              course.catalog_number)
        source_credits += float(course.credits)
    source_course_list = source_course_list.strip('/')

    row_id_str = row_id_str + '-'

    # Build the destination part of the rule group
    destination_credits = 0.0
    discipline = ''
    destination_course_list = ''
    for course in group.destination_courses:
      course_catalog_number = course.catalog_number
      row_id_str += '{}:'.format(course.course_id)
      if discipline != course.discipline:
        if discipline != '': destination_course_list = destination_course_list.strip('/') +'; '
        discipline = course.discipline
        discipline_str = '<span title="{}">{}</span>'.format(course.discipline_name,
                                                             course.discipline)
        destination_course_list = destination_course_list.strip('/ ') + discipline_str + '-'

      if abs(float(course.credits) - course.transfer_credits) > 0.09:
        course_catalog_number += ' ({} cr.)'.format(course.transfer_credits)
      destination_course_list += \
            '<span title="course id: {}">{}</span>/'.format(course.course_id, course_catalog_number)
      destination_credits += float(course.transfer_credits)

    destination_course_list = destination_course_list.strip('/')

    row_id_str = row_id_str.strip(':')
    row_class = 'rule'
    if source_credits != destination_credits:
      row_class = 'rule credit-mismatch'

    # If the rule has been evaluated, the last column is a link to the review history. But if it
    # hasn't been evaluated yet, the last column is just the text that says so.
    status_cell = status_string(group.status)
    if group.status != 0:
      status_cell = '<a href="/history/{}" target="_blank">status_cell</a>'.format(key)
    row = """ <tr id="{}" class="{}">
                <td title="{}">{}</td>
                <td>{}</td>
                <td title="{}">=></td>
                <td title="{}">{}</td>
                <td>{}</td>
                <td>{}</td>
              </tr>"""\
            .format(row_id_str, row_class,
                    institution_names[group.source_institution],
                    re.search('\D+', group.source_institution).group(0),
                    source_course_list,
                    '{}=>{}'.format(source_credits,destination_credits),
                    institution_names[group.destination_institution],
                    re.search('\D+', group.destination_institution).group(0),
                    destination_course_list,
                    status_cell)
    table += '  {}\n'.format(row)

  table += '</tbody></table>'
  return table

if __name__ == "__main__":
  parser = argparse.ArgumentParser('Testing transfer rule groups')
  parser.add_argument('--debug', '-d', action='store_true', default=False)
  args = parser.parse_args()

  if args.debug: DEBUG = true

  fp = open('qbcc-ph.json', 'r')
  records = json.load(fp)
  fp.close()
  table = extract_groups(records)
  html = """
  <head>
    <title>Testing Transfer Rule Groups</title>
    <style>
      table {border-collapse: collapse;}
      td, th {border: 1px solid #ccc; padding:0.25em;}
    </style>
  </head>
  <body>
    {}
  </body>
  """.format(table)
  with open('rules.html', 'w') as r:
    r.write(html)
