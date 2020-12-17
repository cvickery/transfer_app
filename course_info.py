#! /usr/bin/env python3
""" Complete info about a course
"""
import sys
from pgconnection import PgConnection


def expand_rd(rd):
  if rd == 'RLA':
    return 'This is a Liberal Arts course, but it does not satisfy a Pathways requirement.'
  if rd == 'NRL':
    return 'This is not a Liberal Arts course.'
  try:
    return f'{designations[rd]}'
  except KeyError as ke:
    return f'Unknown Designation!'


def _course_info(course_id_str: str):
  """ Return a table telling all about a course.
  """

  try:
    course_id, offer_nbr = course_id_str.split(':')
    offer_nbr = int(offer_nbr)
  except ValueError as ve:
    course_id = course_id_str.strip()
    offer_nbr = 1

  conn = PgConnection()
  cursor = conn.cursor()
  cursor.execute('select * from cuny_institutions')
  colleges = {i.code: i.name for i in cursor.fetchall()}
  cursor.execute(f'select * from cuny_courses where course_id = %s',
                 (course_id, ))
  if cursor.rowcount < 1:
    title = '<h1 class="error">Course not found</h1>'
    result = '<p>The course you requested does not appear to match any course in CUNYfirst.</p>'
    result += f'<p>{course_id}:{offer_nbr}'
  else:
    info = dict()
    for row in cursor.fetchall():
      info[int(row.offer_nbr)] = row
    if offer_nbr not in info:
      title = '<h1 class="error">Course not found</h1>'
      result = '<p>The course you requested does not appear to match any course in CUNYfirst.</p>'
      result += f'<p>{course_id}:{offer_nbr}'
    else:
      course = info[offer_nbr]
      college = colleges[course.institution]
      title = f'<h1>{college} {course.discipline} {course.catalog_number}: <em>{course.title}</em></h1>\n'
      result = '<table><tr><th>Property</th><th>Value</th></tr>\n'
      if cursor.rowcount > 1:
        result += ('<tr><th>Cross-listed with</th><td>' + '<br>'.join([f'{info[a].discipline} '
                                                                      f'{info[a].catalog_number}'
                                                                     for a in info
                                                                     if a != offer_nbr])
                   + '</td></tr>\n')
      result += f'<tr><th>Description</th><td> {course.description} </td></tr>\n'
      gened_text = expand_rd(course.designation)
      result += f'<tr><th>General Education</th><td> {gened_text} </td></tr>\n'
      result += f'<tr><th>Transfers To</th><td> ... </td></tr>\n'
      result += f'<tr><th>Transfers From</th><td> ... </td></tr>\n'
      wric = 'Yes' if 'WRIC' in course.attributes else 'No'
      result += f'<tr><th>Writing Intensive</th><td>{wric}</td></tr>\n'
      result += '</table>'
  conn.close()
  return title, result


if __name__ == '__main__':
  print(_course_info(sys.argv[1]))
