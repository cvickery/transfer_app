#! /usr/local/bin/python3

from app_header import header
from collections import namedtuple, defaultdict
import psycopg
from psycopg.rows import namedtuple_row

# Dict of CUNY college names
conn = psycopg.connect('dbname=cuny_curriculum')
cursor = conn.cursor(row_factory=namedtuple_row)
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
  """  institution            | text
       requirement_id         | text
       requirement_name       | text
       num_ourses_required    | text
       course_alternatives    | text
       conjunction            | text
       num_credits_required   | text
       credit_alternatives    | text
       program_qualifiers     | jsonb
       requirement_qualifiers | jsonb
       context                | jsonb
  """
  req_str = ''
  program_info = program_dict[(req.institution, req.requirement_id)]

  if req.num_courses_required != '0':
    try:
      n = int(req.num_courses_required)
      suffix = '' if n == 1 else 's'
      req_str = f'{n:,} course{suffix}'
    except ValueError:
      req_str = f'{req.num_courses_required} courses'
  if req.num_credits_required != '0':
    and_or = f' {req.conjunction.lower()} ' if req_str else ''
    try:
      n = float(req.num_credits_required)
      suffix = '' if n == 1 else 's'
      req_str += f'{and_or}{n:0.1f,} credit{suffix}'
    except ValueError:
      req_str += f'{and_or}{req.num_credits_required} credits'

  alt_str = ''
  if req.course_alternatives != '0':
    try:
      n = int(req.course_alternatives)
      suffix = '' if n == 1 else 's'
      alt_str = f'{n:,} course{suffix}'
    except ValueError:
      alt_str = f'{req.course_alternatives} courses'
  if req.credit_alternatives != '0':
    and_or = '' if alt_str == '' else '; '
    try:
      n = float(req.credit_alternatives)
      suffix = '' if n == 1 else 's'
      alt_str += f'{and_or}{n:0.1f,} credit{suffix}'
    except ValueError:
      alt_str += f'{and_or}{req.credit_alternatives} credits'
  if alt_str == '':
    alt_str = 'None'

  if req.context:
    ctx_str = ' • ' + '<br> • '.join(req.context)
  else:
    ctx_str = ''

  if req.program_qualifiers:
    prog_qual_str = '<br/>'.join([f'• {q}' for q in req.program_qualifiers])
  else:
    prog_qual_str = ''

  if req.requirement_qualifiers:
    rqmt_qual_str = '<br/>'.join([f'• {q}' for q in req.requirement_qualifiers])
  else:
    rqmt_qual_str = ''

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
  <td>{prog_qual_str}</td>
  <td>{rqmt_qual_str}</td>
  <td>{ctx_str}</td>
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
    conn = psycopg.connect('dbname=cuny_curriculum')
    cursor = conn.cursor(row_factory=namedtuple_row)
    cursor.execute(f"""
    select r.*, b.block_type
      from program_requirements r, requirement_blocks b
     where r.id in (select program_requirement_id
                      from course_requirement_mappings
                     where course_id = {course_id})
       and b.institution = '{institution}'
       and b.requirement_id = r.requirement_id
    """)
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
      <th>Program Qualifiers</th>
      <th>Requirement Qualifiers</th>
    </tr>"""
    skipped_majors = skipped_minors = skipped_concentrations = skipped_limit = 0
    for row in cursor.fetchall():
      if row.block_type in program_types and int(row.course_alternatives) <= count_limit:
        body += _format_requirement(row)
      else:
        if int(row.course_alternatives) > count_limit:
          skipped_limit += 1
        else:
          # Count others only if not already skipped by the alternatives limit
          if row.block_type == 'MAJOR':
            skipped_majors += 1
          if row.block_type == 'MINOR':
            skipped_minors += 1
          if row.block_type == 'CONC':
            skipped_concentrations += 1

    body += '</table>'
    if (skipped_majors + skipped_minors + skipped_concentrations + skipped_limit) > 0:
      if count_limit < 999999:
        suffix = '' if count_limit == 1 else 's'
        body += (f'<p>Skipped {skipped_limit} requirements with more than {count_limit} course '
                 f'alternative{suffix}.</p>')
      situations = {'major': (skipped_majors, '' if skipped_majors == 1 else 's'),
                    'minor': (skipped_minors, '' if skipped_minors == 1 else 's'),
                    'concentration': (skipped_concentrations,
                                      '' if skipped_concentrations == 1 else 's')}
      for situation in situations.keys():
        if situations[situation][0]:  # number skipped
          body += f'<p>Skipped {situations[situation][0]} {situation}{situations[situation][1]}</p>'

    return f'<details open="open">{summary}<hr>{body}</details>'

  else:
    return '<p>Select a course to continue.</p>'


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

  # if nothing selected, select all
  if show_majors is None and show_minors is None and show_concs is None:
    show_majors = 'majors'
    show_minors = 'minors'
    show_concs = 'concs'

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

  try:
    range_index = int(request.args.get('count-limit'))
    count_limit = [1, 2, 5, 10, 20, 50, 100, 999999][range_index]
  except TypeError:
    range_index = 7
    count_limit = 999999
  if count_limit > 100:
    range_string = 'all'
  else:
    range_string = f'{count_limit}'

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
      requests to <a href="mailto:christopher.vickery@qc.cuny.edu?subject='Program Requirements'">
      Christopher Vickery</a>
    </p>
  </div>
  """
  conn = psycopg.connect('dbname=cuny_curriculum')
  cursor = conn.cursor(row_factory=namedtuple_row)

  # Look up all colleges; preselect one if known.
  cursor.execute('select code, prompt from cuny_institutions')
  if institution:
    college_choices = f'<details><summary>Select College ({institution})</summary><hr>'
  else:
    college_choices = '<details open="open"><summary>Select College</summary><hr>'
  if len(colleges_indexed):
    college_choices += """
  <p>
    The numbers tell how many (majors / minors / concentrations) have been indexed for each college.
    During development, not all colleges are being indexed. If a college is not listed here it means
    it is not currently indexed.
  </p>
  """
  else:
    college_choices += 'No colleges are currently indexed.'

  college_choices += '<div class="selections">'
  for college, counts in colleges_indexed.items():
    num_majors = num_minors = num_concs = 0
    if 'MAJOR' in counts.keys():
      num_majors = counts['MAJOR']
    if 'MINOR' in counts.keys():
      num_minors = counts['MINOR']
    if 'CONC' in counts.keys():
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
      discipline_choices = f'<details><summary>Select Discipline ({discipline})</summary><hr>'
    else:
      discipline_choices = '<details open="open"><summary>Select Discipline</summary><hr>'
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
      submit_prompt = 'Change course, discipline, and/or college'
      catalog_choices = (f'<details><summary>Select Course ({discipline} {catalog_number})'
                         f'</summary><hr>')
    else:
      submit_prompt = 'Select a course, or a different discipline and/or college'
      catalog_choices = '<details open="open"><summary>Select Course</summary><hr>'

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
      catalog_choices += '<p class="error">No Courses Found</p>'
    for row in cursor.fetchall():
      if catalog_number and row.catalog_number == catalog_number:
        selected_item = ' class="selected-item"'
        checked_attr = ' checked="checked"'
        course_dict = {'course_id': row.course_id,
                       'catalog_number': row.catalog_number,
                       'title': row.title}
      else:
        selected_item = checked_attr = ''

      catalog_choices += f"""
      <div class="radio-container">
        <input type="radio" {checked_attr}
               name="catalog-number"
               id="catalog-number-{row.course_id}"{checked_attr}
               value="{row.catalog_number}"/>
        <label{selected_item} for="catalog-number-{row.course_id}">
        {row.discipline} {row.catalog_number}: <em>{row.title}</em>
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
    course_mapping_html = '<p class="warning">No Course Selected Yet</p>'

  result += f"""
  <form method="GET" action="/course_mappings">

    <div class="instructions">
      <p>
        There can be a lot of “clutter” in what gets displayed here. You can uncheck some of the
        checkboxes below to exclude the types of requirements you are not interested in.
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
             name="count-limit" type="range" min="0" max="7" step="1.0" value="{range_index}"/>
             <span>{range_string}</span>
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
