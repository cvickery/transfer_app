import logging
import sys

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

# Courses page
@app.route('/courses/', methods=['POST', 'GET'])
def courses():
  num_courses = 0
  if request.method == 'POST':
    conn = sqlite3.connect('static/db/courses.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("select name from institutions where code ='{}'".format(request.form['inst']))
    row = c.fetchone()
    result = "<h1>{} Courses</h1>".format(row['name'])
    query = "select * from courses where institution = '{}' order by discipline, number"\
      .format(request.form['inst'])
    c.execute(query)
    for row in c:
      num_courses += 1
      result = result + """
      <p class="catalog-entry"><strong>{}-{} {}</strong> (<em>{}; {}</em>)<br/>
      {:0.1f}hr; {:0.1f}cr; Requisites: <em>{}</em><br/>{} (<em>{}</em>)</p>
      """.format(row['discipline'],
                 row['number'],
                 row['title'],
                 row['career'],
                 row['cuny_subject'],
                 float(row['hours']),
                 float(row['credits']),
                 row['requisites'],
                 row['description'],
                 row['designation'])
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
      <input type="radio" name="inst" id="inst-{}" value="{}"><label for="inst-{}">{}</label>
      """.format(n, row['code'], n, row['name'])
    result = """
    <form method="post" action="">
      {}
      <button type="submit">Please</button>
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
