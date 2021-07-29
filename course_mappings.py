#! /usr/local/bin/python3

import sys

from collections import namedtuple,defaultdict

from app_header import header
from pgconnection import PgConnection

# Dict of CUNY college names
conn = PgConnection()
cursor = conn.cursor()
cursor.execute('select code, name from cuny_institutions')
college_names = {row.code: row.name for row in cursor.fetchall()}

# Dict for identifying programs, keyed by (institution, requirement_id)
ProgramInfo = namedtuple('ProgramInfo', 'block_type block_value query_string')
cursor.execute("""
select institution, requirement_id, block_type, block_value, title
from requirement_blocks
where period_stop = '99999999'
""")
program_dict = {(row.institution, row.requirement_id):
                ProgramInfo._make([row.block_type,
                                   row.block_value,
                                   f'college={row.institution}&requirement-type={row.block_type}&'
                                   f'requirement-name={row.block_value}&period-range=current'])
                for row in cursor.fetchall()}

# Indexing Status
colleges_indexed = defaultdict(dict)
cursor.execute("""
  select count(*), institution, block_type
    from requirement_blocks
  where (institution, requirement_id) in
    (select institution, requirement_id
       from program_requirements
      group by institution, requirement_id)
  group by institution, block_type;
  """)
for row in cursor.fetchall():
  colleges_indexed[row.institution][row.block_type] = row.count

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
       qualifiers           | jsonb
  """
  req_str = ''
  program_info = program_dict[(req.institution, req.requirement_id)]

  if req.num_courses_required != '0':
    try:
      n = int(req.num_courses_required)
      suffix = '' if n == 1 else 's'
      req_str = f'{n:,} course{suffix}'
    except ValueError as ve:
      req_str = f'{req.num_courses_required} courses'
  if req.num_credits_required != '0':
    and_or = f' {req.conjunction.lower()} ' if req_str else ''
    try:
      n = float(req.num_credits_required)
      suffix = '' if n == 1 else 's'
      req_str += f'{and_or}{n:0.1f,} credit{suffix}'
    except ValueError as ve:
      req_str += f'{and_or}{req.num_credits_required} credits'

  alt_str = ''
  if req.course_alternatives != '0':
    try:
      n = int(req.course_alternatives)
      suffix = '' if n == 1 else 's'
      alt_str = f'{n:,} course{suffix}'
    except ValueError as ve:
      alt_str = f'{req.course_alternatives} courses'
  if req.credit_alternatives != '0':
    and_or = '' if alt_str == '' else '; '
    try:
      n = float(req.credit_alternatives)
      suffix = '' if n == 1 else 's'
      alt_str += f'{and_or}{n:0.1f,} credit{suffix}'
    except ValueError as ve:
      alt_str += f'{and_or}{req.credit_alternatives} credits'
  if alt_str == '':
    alt_str = 'None'

  if req.context:
    ctx_str = ' • ' + '<br> • '.join(req.context)
  else:
    ctx_str = ''

  if req.qualifiers:
    qual_str = ' • ' + '<br/>'.join(req.qualifiers)
  else:
    qual_str = ''

  return f"""
<tr>
  <td>{req.requirement_id}</td>
  <td>
    <a href="/requirements/?{program_info.query_string}" target="_blank">
      {program_info.block_type}: {program_info.block_value}</a>
  </td>
  <td>{req.requirement_name}</td>
  <td>{req_str}</td>
  <td>{alt_str}</td>
  <td>{ctx_str}</td>
  <td>{qual_str}</td>
</tr>"""


# _to_html()
# -------------------------------------------------------------------------------------------------
def _to_html(institution: str, discipline: str, course_dict: dict, program_types,
             count_limit) -> str:
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
    select r.*, b.block_type
      from program_requirements r, requirement_blocks b
     where r.id in (select program_requirement_id
                      from course_requirement_mappings
                     where course_id = {course_id})
       and b.institution = '{institution}'
       and b.requirement_id = r.requirement_id
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
      <th>Qualifiers</th>
    </tr>"""
    skipped_majors = skipped_minors = skipped_concentrations = skipped_limit = 0
    for row in cursor.fetchall():
      if row.block_type in program_types and int(row.course_alternatives) <= count_limit:
        body += _format_requirement(row)
      else:
        if row.block_type == 'MAJOR':
          skipped_majors += 1
        if row.block_type == 'MINOR':
          skipped_minors += 1
        if row.block_type == 'CONC':
          skipped_concentrations += 1
        if int(row.course_alternatives) > count_limit:
          skipped_limit += 1

    body += '</table>'
    if (skipped_majors + skipped_minors + skipped_concentrations + skipped_limit) > 0:
      maj_sfx = '' if skipped_majors == 1 else 's'
      min_sfx = '' if skipped_minors == 1 else 's'
      conc_sfx = '' if skipped_concentrations == 1 else 's'
      lim_sfx = '' if count_limit == 1 else 's'
      body += f"""
    <p>
    Skipped {skipped_majors} major requirement{maj_sfx}; {skipped_minors} minor
    requirement{min_sfx}; {skipped_concentrations} concentration requirement{conc_sfx}"""
    if count_limit < 999999:
      body += (f'; {skipped_limit} requirements with more than {count_limit} course '
               f'alternative{lim_sfx}.')
    body += '</p>'

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
  show_majors = request.args.get('show-majors')
  show_minors = request.args.get('show-minors')
  show_concs = request.args.get('show-concs')
  program_types = []
  if show_majors == 'majors':
    program_types.append('MAJOR')
    show_majors = ' checked="checked'
  if show_minors == 'minors':
    program_types.append('MINOR')
    show_minors = ' checked="checked'
  if show_concs == 'concs':
    program_types.append('CONC')
    show_concs = ' checked="checked'
  if len(program_types) == 0:
    program_types = ['MAJOR', 'MINOR', 'CONC']

  count_limit = [1, 2, 5, 10, 20, 50, 100, 999999][int(request.args.get('count-limit'))]

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
  result += """
  <h1>Explore the Course-to-Requirements Database</h1>
  <div class="instructions">
    <p>
      Select a course, to see what program requirements it satisfies. Programs include all Majors,
      Minors, and Concentrations currently offered at the selected college.
    </p>
    <p>
      Requirements are extracted from Degree Works Scribe Blocks.
    </p>
    <p class="error">This project is still under development. Please report errors and feature
      requests to <a href="mailto:cvickery@qc.cuny.edu?subject='Program Requirements'">Christopher
      Vickery</a>
    </p>
  </div>
  """
  conn = PgConnection()
  cursor = conn.cursor()

  # Look up all colleges; preselect one if known.
  cursor.execute('select code, prompt from cuny_institutions')
  if institution:
    college_choices = f'<details><summary>Select College ({institution})</summary>'
  else:
    college_choices = f'<details open="open"><summary>Select College</summary>'
  if len(colleges_indexed):
    college_choices += """
  <p>
    The numbers tell how many (majors / minors / concentrations) have been indexed for each college.
    During development, not all colleges are being indexed. If a college is not listed here it means
    it is not currently indexed.
  </p>
  """
  else:
    college_choices += 'No colleges have been indexed right now.'

  college_choices += '<div class="selections">'
  for college, counts in colleges_indexed.items():
    num_majors = counts['MAJOR']
    num_minors = counts['MINOR']
    num_concs = counts['CONC']
    if num_majors + num_minors + num_concs > 0:
      if college == institution:
        selected_item = ' class="selected-item"'
        checked_attr = 'checked="checked"'
      else:
        selected_item = checked_attr = ''
      college_choices += f"""
      <div class="radio-container">
        <input id="radio-{college}" {checked_attr}
               type="radio"
               name="college"
               value="{college}" />
        <label{selected_item} for="radio-{college}">{college_names[college]}<br/>
        <span>({num_majors} / {num_minors} / {num_concs})</span></label>
      </div>
      """
  college_choices += '</div></details>'

  # If there is an institution, display all disciplines
  if institution:
    submit_prompt = 'Select a discipline or a different college'
    if discipline:
      discipline_choices = f'<details><summary>Select Discipline ({discipline})</summary>'
    else:
      discipline_choices = f'<details open="open"><summary>Select Discipline</summary>'
    discipline_choices += '<div class="selections">'

    cursor.execute("""
    select discipline, discipline_name, department
      from cuny_disciplines
     where institution = %s
       and cuny_subject != 'MESG'
       and status = 'A'
     """, (institution,))
    for row in cursor.fetchall():
      if discipline and discipline.lower() == row.discipline.lower():
        selected_item = ' class="selected-item"'
        checked_attr = 'checked="checked"'
      else:
        selected_item = checked_attr = ''
      discipline_choices += f"""
      <div class="radio-container">
        <input id="radio-{row.discipline}" {checked_attr}
               type="radio"
               name="discipline"
               value="{row.discipline}" />
        <label{selected_item} for="radio-{row.discipline}">
          {row.discipline} ({row.discipline_name})
        </label>
      </div>
    """
    discipline_choices += '</div></details>'
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
    if cursor.rowcount == 0:
      catalog_choices += f'<p class="error">No Courses Found</p>'
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

  if course_dict:
    course_mapping_html = _to_html(institution, discipline, course_dict, program_types, count_limit)
  else:
    course_mapping_html = '<p class="error">No Requirements Found</p>'

  result += f"""
  <form method="GET" action="/course_mappings">

    <div class="instructions">
      <p>
        There can be a lot of “clutter” in what gets displayed here. You can use the checkboxes
        below to include only the types of requirements you are interested in.
      </p>
      <div>
        <div class="inline">
          <input type="checkbox" id="show-majors" name="show-majors" value="majors"{show_majors}/>
          <label for="show-majors">Majors</label>
        </div>
        <div class="inline">
          <input type="checkbox" id="show-minors" name="show-minors" value="minors"{show_minors}/>
          <label for="show-minors">Minors</label>
        </div>
        <div class="inline">
          <input type="checkbox" id="show-concs" name="show-concs" value="concs"{show_concs}/>
          <label for="show-concs">Concentrations</label>
        </div>
      </div>
      <hr>
      <p>
        Another potential source of clutter is requirements that can be satisified by a large number
        of courses. You an use the slider below to filter out requirements based on how many courses
        can satisfy them.
      </p>
      <input id="slider"
             name="count-limit" type="range" min="0" max="7" step="1.0"/> <span>all</span>
    </div>

    <div id="select-institution">
      {college_choices}
    </div>

    <div id="select-discipline">
      {discipline_choices}
    </div>

    <div id="select-catalog-num">
      {catalog_choices}
    </div>

    <div>
      <button type="submit" id="goforit">{submit_prompt}</button>
    </div>

    <div id="course-mapping">
      {course_mapping_html}
    </div>
  </form>
  """
  return result
