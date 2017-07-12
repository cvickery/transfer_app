import logging
import sys

import datetime
import sqlite3

from flask import Flask, url_for, render_template, redirect, send_file, Markup, request

app = Flask(__name__)


@app.route('/favicon.ico')
def favicon():
  return send_file('favicon.ico', mimetype = "image/x-icon")

@app.route('/image/<file_name>')
def image_file(file_name):
  return send_file('static/images/' + file_name + '.png')

@app.route('/')
@app.route('/index')
def index():
  return render_template('index.html')

@app.route('/assessment')
def assessment():
  return render_template('assessment.html')

# COURSES PAGE
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
      <div><button type="submit">Please</button></div>
    <form>
    """.format(prompt)
  return render_template('courses.html', result=Markup(result))


# TRANSFERS PAGE
# User submits a CUNY email address and lists of sending colleges, external subjects, receiving
# colleges, and course attributes. Lists may be empty, which means "all." (No email address means
# "none.")
# Show a form that can be used to verify the corresponding transfer rules or to note anomalies.
@app.route('/transfers/', methods=['POST', 'GET'])
def transfers():
  num_courses = 0
  if request.method == 'POST':
    # User has submitted the form. They must have supplied a cuny email addresss, a list of sending
    # colleges, a list of external subject areas, and a list of receiving colleges.

    # Get sending college(s)
    # Get cuny subject(s) for receiving college(s)
    # Get receiving college(s)
    # Verify the email address. It must match the single receiving college's domain. Otherwise, the
    # user is in view-only mode.
    #
    # select distinct c.description, i.institution, i.discipline
    #   from cuny_subjects c, courses i
    #   where i.cuny_subject = c.area
    #   order by i.institution, discipline;
    #
    conn = sqlite3.connect('static/db/courses.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("select * from external_subjects")
    cuny_subjects = {row['area']:row['description'] for row in c}

    c.execute("select * from careers")
    careers = {(row['institution'], row['career']): row['description'] for row in c}

    c.execute("select * from designations")
    designations = {row['designation']: row['description'] for row in c}

    result = ''
    sources = request.form.getlist('source')
    for source in sources:
      result = result + '<p>{}</p>'.format(source)

  # Form not submitted yet, so generate it.
  else:
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
    <form method="post" action="">
      <fieldset>
      {}
      {}
      {}
      <fieldset><legend>Your email address</legend>
      <p>This must be a valid CUNY email address.</p>
      <div>
        <input type="text" name="email" id="email-text"/>
      </div>
      <div><button type="submit">Please</button></div>
      </fieldset>
    <form>
    """.format(source_prompt, destination_prompt, destination_disciplines_prompt)
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
