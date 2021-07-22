#! /usr/local/bin/python3

import sys

from app_header import header
from pgconnection import PgConnection

# Dict of CUNY college names
conn = PgConnection()
cursor = conn.cursor()
cursor.execute('select code, name from cuny_institutions')
college_names = {row.code: row.name for row in cursor.fetchall()}

# Dict of current block_types, keyed by (institution, requirement_id)
cursor.execute("""
select institution, requirement_id, block_type, block_value, title
from requirement_blocks
where period_stop = '99999999'
""")
block_values = {(row.institution, row.requirement_id): row.block_value for row in cursor.fetchall()}

conn.close()


# _format_requirement()
# -------------------------------------------------------------------------------------------------
def _format_requirement(req) -> str:
  """  institution          | text
       requirement_id       | text
       requirement_name     | text
       num_ourses_required  | text
       course_alternatives  | text
       conjunction          | text
       num_credits_required | text
       credit_alternatives  | text
       context              | jsonb
  """
  req_str = ''
  block_value = block_values[(req.institution, req.requirement_id)]

  if req.num_courses_required != '0':
    try:
      n = int(req.num_courses_required)
      suffix = '' if n == 1 else 's'
      req_str = f'{n} course{suffix}'
    except ValueError as ve:
      req_str = f'{req.num_courses_required} courses'
  if req.num_credits_required != '0':
    and_or = f' {req.conjunction.lower()} ' if req_str else ''
    try:
      n = float(req.num_credits_required)
      suffix = '' if n == 1 else 's'
      req_str += f'{and_or}{n:0.1f} credit{suffix}'
    except ValueError as ve:
      req_str += f'{and_or}{req.num_credits_required} credits'

  alt_str = ''
  if req.course_alternatives != '0':
    try:
      n = int(req.course_alternatives)
      suffix = '' if n == 1 else 's'
      alt_str = f'{n} course{suffix}'
    except ValueError as ve:
      alt_str = f'{req.course_alternatives} courses'
  if req.credit_alternatives != '0':
    and_or = '' if alt_str == '' else '; '
    try:
      n = float(req.credit_alternatives)
      suffix = '' if n == 1 else 's'
      alt_str += f'{and_or}{n:0.1f} credit{suffix}'
    except ValueError as ve:
      alt_str += f'{and_or}{req.credit_alternatives} credits'
  if alt_str == '':
    alt_str = 'None'
  return f"""
<tr>
  <td>{req.requirement_id}</td>
  <td>{block_value}</td>
  <td>{req.requirement_name}</td>
  <td>{req_str}</td>
  <td>{alt_str}</td>
  <td>{req.context}</td>
</tr>"""


# _to_html()
# -------------------------------------------------------------------------------------------------
def _to_html(institution: str, discipline: str, course_dict: dict) -> str:
  """
  """
  if institution and discipline and course_dict:
    college = college_names[institution]
    catalog_number = course_dict['catalog_number']
    course_id = int(course_dict['course_id'])
    title = course_dict['title']
    conn = PgConnection()
    cursor = conn.cursor()
    cursor.execute(f"""
    select * from program_requirements
     where id in (select program_requirement_id from course_requirement_mappings where course_id = {course_id})
    """)
    print(cursor.query)
    suffix = '' if cursor.rowcount == 1 else 's'
    summary = (f'<summary>{discipline} {catalog_number} ({course_id:06}) Satisfies '
               f'{cursor.rowcount} requirement{suffix} at {college}</summary>')
    body = """<table>
    <tr>
      <th>Requirement ID</th>
      <th>Program</th>
      <th>Requirement Name</th>
      <th>Requirement</th>
      <th>Alternatives</th>
      <th>Context</th>
    </tr>"""
    body += '\n'.join([_format_requirement(row) for row in cursor.fetchall()])
    body += '</table>'
    return f'<details>{summary}{body}</details>'
  else:
    return '<p>Select a Course.</p>'


# /course_mappings_impl()
# -------------------------------------------------------------------------------------------------
def course_mappings_impl(request):
  """ Return a view of the program requirements a course satisfies.
      If the instutition, discipline, or course_dict are not known, return a form to get them
      instead.
  """
  institution = request.args.get('college')
  discipline = request.args.get('discipline')
  catalog_number = request.args.get('catalog-number')
  course_dict = None
  header_str = header(title='Requirements by Course',
                      nav_items=[{'type': 'link',
                                          'text': 'Main Menu',
                                          'href': '/'
                                  },
                                 {'type': 'link',
                                  'text': 'Programs',
                                  'href': '/registered_programs'
                                  }])
  result = f'{header_str}'
  conn = PgConnection()
  cursor = conn.cursor()

  # Look up all colleges; preselect one if known.
  cursor.execute('select code, prompt from cuny_institutions')
  if institution:
    college_choices = f'<details><summary>Select College ({institution})</summary>'
  else:
    college_choices = f'<details open="open"><summary>Select College</summary>'
  for row in cursor.fetchall():
    if row.code == institution:
      checked_attr = ' checked="checked"'
    else:
      checked_attr = ''
    college_choices += f"""
    <div class="inline-college">
      <input id="radio-{row.code}"
             type="radio" {checked_attr}
             name="college"
             value="{row.code}" />
      <label for="radio-{row.code}">{row.prompt}</label>
    </div>
    """
  college_choices += '</details>'

  # If there is an institution, display all disciplines
  if institution:
    submit_prompt = 'Select a discipline or a different college'
    if discipline:
      discipline_choices = f'<details><summary>Select Discipline ({discipline})</summary>'
    else:
      discipline_choices = f'<details open="open"><summary>Select Discipline</summary>'
    cursor.execute("""
    select discipline, discipline_name, department
      from cuny_disciplines
     where institution = %s
       and cuny_subject != 'MESG'
       and status = 'A'
     """, (institution,))
    for row in cursor.fetchall():
      if discipline and discipline.lower() == row.discipline.lower():
        checked_attr = ' checked="checked"'
      else:
        checked_attr = ''
      discipline_choices += f"""
      <div class="inline-discipline">
        <input id="radio-{row.discipline}"
               type="radio" {checked_attr}
               name="discipline"
               value="{row.discipline}" />
        <label for="radio-{row.discipline}">{row.discipline} ({row.discipline_name})</label>
      </div>
    """
    discipline_choices += '</details>'
  else:
    submit_prompt = 'Select a College'
    discipline_choices = ''

  # If there is a discipline, display all courses
  if discipline:
    if catalog_number:
      submit_prompt = 'Select a different course, discipline, and/or college'
      catalog_choices = f'<details><summary>Select Course ({discipline} {catalog_number})</summary>'
      # catalog_choices += f'<input type="hidden" name="catalog-number" value="{catalog_number}"/>'
    else:
      submit_prompt = 'Select a course, or a different discipline and/or college'
      catalog_choices = f'<details open="open"><summary>Select Course</summary>'

    cursor.execute("""
    select course_id, offer_nbr, discipline, catalog_number, title
      from cuny_courses
     where institution = %s
       and discipline = %s
       and career = 'UGRD'
       and designation not in ('MLA', 'MNL')
       and course_status = 'A'
     order by numeric_part(catalog_number)
    """, (institution, discipline))
    for row in cursor.fetchall():
      if catalog_number and row.catalog_number == catalog_number:
        selected_course_attr = ' class="selected-course"'
        course_dict = {'course_id': row.course_id,
                       'catalog_number': row.catalog_number,
                       'title': row.title}
      else:
        selected_course_attr = ''
        checked_attr = ''

      catalog_choices += f"""
      <div{selected_course_attr}>
        <input type="radio"
               name="catalog-number"
               id="catalog-number-{row.course_id}"{checked_attr}
               value="{row.catalog_number}"/>
        <label for="catalog-number-{row.course_id}">
          {row.discipline} {row.catalog_number}: {row.title}
        </label>
      </div>
      """
    catalog_choices += '</details>'
  else:
    submit_prompt = 'Select a discipline or a different college'
    catalog_choices = ''

  conn.close()

  course_mapping_html = _to_html(institution, discipline, course_dict)

  result += f"""
  <form method="GET" action="/course_mappings">

    <div id="select-institution">
      {college_choices}
    </div>

    <div id="select-discipline">
      {discipline_choices}
    </div>

    <div id="select-catalog-num">
      {catalog_choices}
    </div>

    <div id="goforit">
      <button type="submit">{submit_prompt}</button>
    </div>

    <div id="course-mapping">
      {course_mapping_html}
    </div>
  </form>
  """
  return result
