import logging
import sys
import os

import datetime
import sqlite3

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
  result = """
    <form method="post" action="" id="form-0">
      <fieldset>
      {}
      {}
      <fieldset><legend>Your email address</legend>
      <p>This must be a valid CUNY email address.</p>
      <div>
        <input type="text" name="email" id="email-text"/>
      </div>
      <div>
        <div id="error-msg" class="error"> </div>
        <input type="hidden" name="form" value="form_1" />
        <button type="submit" id="submit-form-0">Next</button>
      </div>
      </fieldset>
    <form>
    """.format(source_prompt, destination_prompt)
  return render_template('transfers.html', result=Markup(result))

def form_1(request, session):
  """ Generate form_2: Filter disciplines
  """
  # Capture form data in user's session
  session['sources'] = request.form.getlist('source')
  session['destinations'] = request.form.getlist('destination')
  session['email'] = request.form.get('email')

  # Get filter info

  institutions = set(session['sources']) | set(session['destinations'])
  institution_list = "('" + "', '".join(institutions) + "')"
  q = """
  select t.source_course_id as source_id,
         c1.institution as source_institution,
         c1.discipline || c1.number as source_course,
         t.destination_course_id as destination_id,
         c2.institution as destination_institution,
         c2.discipline || c2.number as destination_course
    from transfer_rules t, courses c1, courses c2
    where
          c1.institution in {} and c2.institution in {}
      and c1.course_id = t.source_course_id
      and c2.course_id = t.destination_course_id
    order by source_institution, destination_institution, source_course
  """.format(institution_list, institution_list)
  conn = sqlite3.connect('static/db/courses.db')
  conn.row_factory = sqlite3.Row
  c = conn.cursor()


  c.execute("select * from cuny_subjects")
  cuny_subjects = {row['area']:row['description'] for row in c}

  c.execute("select * from careers")
  careers = {(row['institution'], row['career']): row['description'] for row in c}

  c.execute("select * from designations")
  designations = {row['designation']: row['description'] for row in c}



  result = """
  <h1>Filter Transfer Rules</h1>
  {}
  <form method="post" action="" id="form-1">
    <fieldset>
      <input type="hidden" name="form" value="form_2" />
      <button type="submit" id="form-1-submit">Next</button>
    </fieldset>
  </form>
  """.format(q)
  return render_template('transfers.html', result=Markup(result))

def form_2(request, session):
  """ Generate form_3: Collect transfer rule evaluations
  """
  result = '<h1>Form 2 not implemented yet</h1>'
  result = """
  <h1>Evaluate Transfer Rules</h1>
  <form method="post" action="" id="form-2">
    <fieldset>
      <input type="hidden" name="form" value="form_3" />
      <button type="submit" id="form-1-submit">Next</button>
    </fieldset>
  </form>
  """
  return render_template('transfers.html', result=Markup(result))

def form_3(request, session):
  result = '<h1>Confirmation page not implemented yet</h1>'
  return render_template('transfers.html', result=Markup(result))

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
# Allows user to pick a college, and see catalog descriptions of all courses offered there.
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
    c.execute("select name, date_updated from institutions where code ='{}'".format(institution_code))
    row = c.fetchone()
    institution_name = row['name']
    date_updated = datetime.datetime.strptime(row['date_updated'], '%Y-%m-%d').strftime('%B %d, %Y')
    num_active_courses = c.execute("""
        select count(*) from courses where institution = '{}' and status='A'
        """.format(institution_code)).fetchone()[0]

    result = """
      <h1>{} Courses</h1><p class='subtitle'>{:,} active courses as of {}</p>
      """.format(institution_name, num_active_courses, date_updated)

    query = "select * from courses where institution = '{}' and status = 'A' order by discipline, number"\
      .format(institution_code)
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
