import logging
import sys
import os

import datetime
import sqlite3

from collections import namedtuple

from flask import Flask, url_for, render_template, redirect, send_file, Markup, request, session
app = Flask(__name__)
app.secret_key = os.urandom(24)

#
# Overhead URIs
@app.route('/favicon.ico')
def favicon():
  return send_file('favicon.ico', mimetype = "image/x-icon")

@app.route('/image/<file_name>')
def image_file(file_name):
  return send_file('static/images/' + file_name + '.png')

def error():
  result = "<h1>Error</h1>"
  return render_template('transfers.html', result=Markup(result))

#
# QC Applications
# =================================================================================================
# Index: Require user to sign in using  QC email address, and provide a menu of applications.
# Assessment: Demonstrate accessing G-Suite Assessment repository info.

# INDEX
# -------------------------------------------------------------------------------------------------
@app.route('/')
@app.route('/index')
def index():
  return render_template('index.html')

# ASSESSMENT
# -------------------------------------------------------------------------------------------------
@app.route('/assessment')
def assessment():
  return render_template('assessment.html')


#
# CUNY Applications
# =================================================================================================
# Transfer Pages: A sequence of pages for reviewing transfer rules.
# Courses Page: Display the complete catalog of currently active courses for any college.

# TRANSFERS PAGES
# -------------------------------------------------------------------------------------------------
#   Not posted: display form_1, which displays email prompt, source, and destination lists. User
#   must provide email and select exactly one institution from one of the lists and 1+ institutions
#   from the other list.
#   Posted form_1: display form_2, which provides list of disciplines for the single institution.
#   The user may select 1+ of them.
#   Posted form_2: display form_3, which provides matching transfer rules for all discipline pairs
#   selected. For each one, display a "verified" checkbox and a "notation" text box.
#   Posted form_3: enter all verified/notation data, along with person's email into db; send email
#   for confirmation. When user replies to the email, mark all matching items as confirmed and
#   notify the proper authorities. If confirmation email says no, notify OUR, who can delete them.
#   (This allows people to accidentally deny their work without losing it.)

# form_0()
# -------------------------------------------------------------------------------------------------
def form_0():
  """ Generate form_1. Source and destination institutions; user's email.
  """
  conn = sqlite3.connect('static/db/courses.db')
  conn.row_factory = sqlite3.Row
  c = conn.cursor()
  c.execute("select * from institutions order by code")
  institution_list = c.fetchall()

  source_prompt = '<fieldset id="sending-field"><legend>Sending College(s)</legend>'
  n = 0
  for row in institution_list:
    n += 1
    source_prompt += """
        <div class='institution-select'>
          <input type="checkbox" name="source" class="source" id="source-{}" value="{}">
          <label for="source-{}">{}</label>
        </div>
    """.format(n, row['code'], n, row['name'])
  source_prompt += """
    <div>
    <button id="all-sources">Select All Sending Colleges</button>
    <button id="no-sources">Clear All Sending Colleges</button>
    </div>
  </fieldset>
  """

  destination_prompt = '<fieldset id="receiving-field"><legend>Receiving College(s)</legend>'
  n = 0
  for row in institution_list:
    n += 1
    destination_prompt += """
        <div class='institution-select'>
          <input type="checkbox" name="destination" class="destination" id="dest-{}" value="{}">
          <label for="dest-{}">{}</label>
        </div>
    """.format(n, row['code'], n, row['name'])
  destination_prompt += """
    <div>
    <button id="all-destinations">Select All Receiving Colleges</button>
    <button id="no-destinations">Clear All Receiving Colleges</button>
    </div>
  </fieldset>
  """
  destination_disciplines_prompt = "<fieldset><legend>Discipline/Subject(s)</legend>"
  destination_disciplines_prompt += "</fieldset>"
  email = ''
  try:
    email = session['email']
  except:
    pass
  result = """
    <form method="post" action="" id="form-0">
      <fieldset>
      {}
      {}
      <fieldset><legend>Your email address</legend>
      <p>This must be a valid CUNY email address.</p>
      <div>
        <input type="text" name="email" id="email-text" value="{}"/>
      </div>
      <div>
        <div id="error-msg" class="error"> </div>
        <input type="hidden" name="form" value="form_1" />
        <button type="submit" id="submit-form-0">Next</button>
      </div>
      </fieldset>
    <form>
    """.format(source_prompt, destination_prompt, email)
  return render_template('transfers.html', result=Markup(result))

# form_1()
# -------------------------------------------------------------------------------------------------
def form_1(request, session):
  """ Generate form_2: Filter disciplines
  """
  # Capture form data in user's session
  session['sources'] = request.form.getlist('source')
  session['destinations'] = request.form.getlist('destination')
  session['email'] = request.form.get('email')

  # Get filter info
  conn = sqlite3.connect('static/db/courses.db')
  conn.row_factory = sqlite3.Row
  c = conn.cursor()

  # Get source and destination institiution names
  c.execute("select * from institutions order by code")
  institution_names = {row['code']: row['name'] for row in c}

  # Look up all the rules for the source and destination institutions
  source_institution_list = "('" + "', '".join(session['sources']) + "')"
  destination_institution_list = "('" + "', '".join(session['destinations']) + "')"
  q = """
  select t.source_course_id as source_id,
         c1.institution as source_institution,
         c1.discipline as source_discipline,
         c1.discipline || ' ' || c1.number as source_course,
         c1.cuny_subject as source_subject,
         t.destination_course_id as destination_id,
         c2.institution as destination_institution,
         c2.discipline as destination_discipline,
         c2.discipline || ' ' || c2.number as destination_course,
         c2.cuny_subject as destination_subject
    from transfer_rules t, courses c1, courses c2
    where
          c1.institution in {} and c2.institution in {}
      and c1.course_id = t.source_course_id
      and c2.course_id = t.destination_course_id
    order by source_institution, destination_institution, source_course
  """.format(source_institution_list, destination_institution_list)
  c.execute(q)
  Rule = namedtuple('Rule', [ 'source_id', 'source_institution', 'source_discipline',
                              'source_course', 'source_subject',
                              'destination_id', 'destination_institution', 'destination_discipline',
                              'destination_course', 'destination_subject'])
  rules = [rule for rule in map(Rule._make, c.fetchall())]

  # Create lists of disciplines for subjects found in the transfer rules
  #   You want a set of institution:discipline pairs for each subject
  source_subjects = {}
  destination_subjects = {}
  for rule in rules:
    if rule.source_subject not in source_subjects:
      source_subjects[rule.source_subject] = set()
    source_subjects[rule.source_subject].add((rule.source_institution,
                                                 rule.source_discipline))
    if rule.destination_subject not in destination_subjects:
      destination_subjects[rule.destination_subject] = set()
    destination_subjects[rule.destination_subject].add((rule.destination_institution,
                                                           rule.destination_discipline))

  sending_is_singleton = False
  sending_suffix = 's’'
  receiving_is_singleton = False
  receiving_suffix ='s’'
  criterion = ''
  if len(session['sources']) == 1:
    criterion = 'the sending college is ' + institution_names[session['sources'][0]]
    sending_is_singleton = True
    sending_suffix = '’s'
  if len(session['destinations']) == 1:
    receiving_is_singleton = True
    receiving_suffix = '’s'
    if criterion != '': criterion += ' and '
    criterion += 'the receiving college is ' + institution_names[session['destinations'][0]]

  c.execute("select * from cuny_subjects")
  cuny_subjects = {row['area']:row['description'] for row in c}

  c.execute("select * from careers")
  careers = {(row['institution'], row['career']): row['description'] for row in c}

  c.execute("select * from designations")
  designations = {row['designation']: row['description'] for row in c}

  # Build filter table. For each cuny_subject found in either sending or receiving courses, list
  # all disciplines at those colleges.
  # tuples are cuny_subject, college, discipline
  Filter = namedtuple('Filter', ['subject', 'college', 'discipline'])
  source_filters = set()
  destination_filters = set()
  for rule in rules:
    source_filters.add(Filter(rule.source_subject,
                              rule.source_institution,
                              rule.source_discipline))
    destination_filters.add(Filter(rule.destination_subject,
                                   rule.destination_institution,
                                   rule.destination_discipline))
  # Table rows with checkboxes for subjects
  all_subjects = set([filter.subject for filter in source_filters])
  all_subjects |= set([filter.subject for filter in destination_filters])
  all_subjects = sorted(all_subjects)
  filter_rows = ''
  for subject in all_subjects:
    # Sending College Disciplines
    source_disciplines = ''
    source_discipline_set = set()
    for filter in source_filters:
      if filter.subject == subject:
        if sending_is_singleton:
          source_discipline_set.add(filter.discipline)
        else:
          source_discipline_set.add((filter.college, filter.discipline))
    if sending_is_singleton:
      if len(source_discipline_set) > 1:
        source_disciplines = '<div>' +'</div><div>'.join(source_discipline_set) + '</div>'
      else:
        source_disciplines = ''.join(source_discipline_set)
    else:
      source_disciplines = ''
      source_discipline_set = sorted(source_discipline_set)
      colleges = {}
      for discipline in source_discipline_set:
        if discipline[0] not in colleges.keys():
          colleges[discipline[0]] = []
        colleges[discipline[0]].append(discipline[1])
      for college in colleges:
        source_disciplines += '<div>{}: <em>{}</em></div>'.format(institution_names[college],
                                                                  ', '.join(colleges[college]))

    # Receiving College Disciplines
    destination_disciplines = ''
    destination_discipline_set = set()
    for filter in destination_filters:
      if filter.subject == subject:
        if receiving_is_singleton:
          destination_discipline_set.add(filter.discipline)
        else:
          destination_discipline_set.add((filter.college, filter.discipline))
    if receiving_is_singleton:
      destination_disciplines = ''
      if len(destination_discipline_set) > 1:
        destination_disciplines = '<div>' +'</div><div>'.join(destination_discipline_set) + '</div>'
      else:
        destination_disciplines = ''.join(destination_discipline_set)
    else:
      destination_disciplines = ''
      destination_discipline_set = sorted(destination_discipline_set)
      colleges = {}
      for discipline in destination_discipline_set:
        if discipline[0] not in colleges.keys():
          colleges[discipline[0]] = []
        colleges[discipline[0]].append(discipline[1])
      for college in colleges:
        destination_disciplines += '<div>{}: <em>{}</em></div>'.format(institution_names[college],
                                                                       ', '.join(colleges[college]))

    filter_rows += """
    <tr>
      <td><input type="checkbox" name="subject" value="{}"/></td>
      <td>{}</td>
      <td>{}</td>
      <td>{}</td>
    </tr>
    """.format(subject, cuny_subjects[subject], source_disciplines, destination_disciplines)

  if len(all_subjects) > 1:
    filter_rows += """
      <tr>
      <td>
        <input type="checkbox" id="all-subjects" />
        <label for="all-subjects"><em> all</em></label></td>
        <td colspan="3"><em>Select All Subjects</em></td>
      </tr>
      <tr>
        <td>
          <input type="checkbox" id="no-subjects" />
          <label for="no-subjects"><em> none</em></label></td>
        <td colspan="3"><em>Clear All Subjects</em></td>
      </tr>
      """
  result = """
  <h1>Filter Transfer Rules</h1>
  <p>There are {:,} rules where {}.</p>
  <p>There are {} source filters and {} destination filters.</p>
  <p>There are {} subjects: {} source subjects and {} destination subjects.</p>
  <form method="post" action="" id="form-1">
    <fieldset>
      <table id="subject-filters">
        <tr>
          <th>Select</th>
          <th>CUNY Subject</th>
          <th>Sending College{} Discipline(s)</th>
          <th>Receiving College{} Discipline(s)</th>
        </tr>
        {}
      </table>
      <a href="" class="restart">Restart</a>
      <input type="hidden" name="form" value="form_2" />
      <button type="submit" id="form-1-submit">Next</button>
    </fieldset>
  </form>
  """.format(len(rules), criterion, len(source_filters), len(destination_filters),
             len(all_subjects), len(source_subjects), len(destination_subjects),
             sending_suffix, receiving_suffix, filter_rows)
  return render_template('transfers.html', result=Markup(result))

# form_2()
# -------------------------------------------------------------------------------------------------
def form_2(request, session):
  """ Generate form_3: Collect transfer rule evaluations
  """
  session['subjects'] = request.form.getlist('subject')
  result = '<h1>Form 2 not implemented yet</h1>'
  result = """
  <h1>Evaluate Transfer Rules</h1>
  <p>Number of subjects: {}</p>
  <form method="post" action="" id="form-2">
    <fieldset>
      <a href="" class="restart">Restart</a>
      <input type="hidden" name="form" value="form_3" />
      <button type="submit" id="form-2-submit">Next</button>
    </fieldset>
  </form>
  """.format(len(session['subjects']))
  return render_template('transfers.html', result=Markup(result))

# form_3()
# -------------------------------------------------------------------------------------------------
def form_3(request, session):
  result = '<h1>Confirmation page not implemented yet</h1>'
  return render_template('transfers.html', result=Markup(result))

# app.route()
# -------------------------------------------------------------------------------------------------
@app.route('/transfers/', methods=['POST', 'GET'])
def transfers():
  # Dispatcher for forms
  dispatcher = {
    'form_1': form_1,
    'form_2': form_2,
    'form_3': form_3,
  }
  if request.method == 'POST':
    # User has submitted a form.
    return dispatcher.get(request.form['form'], lambda: error)(request, session)

  # Form not submitted yet, so generate form_1
  else:
    return form_0()


    # select distinct c.description, i.institution, i.discipline
    #   from cuny_subjects c, courses i
    #   where i.cuny_subject = c.area
    #   order by i.institution, discipline;


# COURSES PAGE
# -------------------------------------------------------------------------------------------------
# Pick a college, and see catalog descriptions of all courses currently active there.
@app.route('/courses/', methods=['POST', 'GET'])
def courses():
  num_courses = 0
  if request.method == 'POST':
    conn = sqlite3.connect('static/db/courses.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("select * from external_subjects")
    cuny_subjects = {row['area']:row['description'] for row in c}

    c.execute("select * from careers")
    careers = {(row['institution'], row['career']): row['description'] for row in c}

    c.execute("select * from designations")
    designations = {row['designation']: row['description'] for row in c}

    institution_code = request.form['inst']
    c.execute("""
              select name, date_updated
                from institutions
               where code ='{}'
               """.format(institution_code))
    row = c.fetchone()
    institution_name = row['name']
    date_updated = datetime.datetime.strptime(row['date_updated'], '%Y-%m-%d').strftime('%B %d, %Y')
    num_active_courses = c.execute("""
        select count(*) from courses where institution = '{}' and status='A'
        """.format(institution_code)).fetchone()[0]

    result = """
      <h1>{} Courses</h1><p class='subtitle'>{:,} active courses as of {}</p>
      """.format(institution_name, num_active_courses, date_updated)

    query = """
      select * from courses
       where institution = '{}'
         and status = 'A'
       order by discipline, number
       """.format(institution_code)
    c.execute(query)

    for row in c:
      num_courses += 1
      result = result + """
      <p class="catalog-entry"><strong>{} {}: {}</strong> (<em>{}; {}</em>)<br/>
      {:0.1f}hr; {:0.1f}cr; Requisites: <em>{}</em><br/>{} (<em>{}</em>)</p>
      """.format(row['discipline'],
                 row['number'].strip(),
                 row['title'],
                 careers[(row['institution'],row['career'])],
                 cuny_subjects[row['cuny_subject']],
                 float(row['hours']),
                 float(row['credits']),
                 row['requisites'],
                 row['description'],
                 designations[row['designation']])

  # Form not submitted yet or institution has no courses
  if num_courses == 0:
    prompt = '<fieldset><legend>Select a College</legend>'
    conn = sqlite3.connect('static/db/courses.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("select * from institutions order by code")
    n = 0
    for row in c:
      n += 1
      prompt = prompt + """
      <div class='institution-select'>
        <input type="radio" name="inst" id="inst-{}" value="{}">
        <label for="inst-{}">{}</label>
      </div>
      """.format(n, row['code'], n, row['name'])
    result = """
    <form method="post" action="">
      {}
      <div>
        <button type="submit">Please
        </button>
      </div>
    <form>
    """.format(prompt)
  return render_template('courses.html', result=Markup(result))



@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=5000, debug=True)
