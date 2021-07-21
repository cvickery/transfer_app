#! /usr/local/bin/python3

import sys
from app_header import header
from pgconnection import PgConnection


# _to_html()
# -------------------------------------------------------------------------------------------------
def _to_html(institution: str, discipline: str, course_dict: dict) -> str:
  """
  """
  if institution and discipline and course_dict:
    catalog_number = course_dict['catalog_number']
    title = course_dict['title']
    summary = f'<summary>{institution} {discipline} {catalog_number} <em>{title}</em></summary>'
    conn = PgConnection()
    course_cursor = conn.cursor()
    requirement_cursor = conn.cursor()
    course_cursor.execute("""
    select * from course_program_mappings
    where course_id = %s
    """, (course_dict['course_id'], ))
    print(course_cursor.query, file=sys.stderr)
    body = ''
    for row in course_cursor.fetchall():
      print(row, file=sys.stderr)
      program_requirement_id = int(row.program_requirement_id)
      requirement_cursor.execute(f"""
      select *
        from program_requirements
       where id = {program_requirement_id}
      """)
      body = '\n'.join([f'<p>{row}</p>' for row in requirement_cursor.fetchall()])
    return f'<details>{summary}{body}</details>'
  else:
    return '<p>Provide more information.</p>'


# /course_mappings_impl()
# -------------------------------------------------------------------------------------------------
def course_mappings_impl(request):
  """ Return a view of the program requirements a course satisfies.
      If the instutition, discipline, or catalog_num are not known, return a form to get them
      instead.
  """
  institution = request.args.get('college')
  discipline = request.args.get('discipline')
  catalog_number = request.args.get('catalog-number')
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
    course_dict = None
    for row in cursor.fetchall():
      if catalog_number and row.catalog_number == catalog_number:
        checked_attr = ' checked="checked"'
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
