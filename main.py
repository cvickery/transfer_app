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
  if request.method == 'POST':
    conn = sqlite3.connect('static/db/courses.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = "select * from courses where institution = '{}'".format(request.form['institution'].upper())
    c.execute(query)
    result = ''
    for row in c:
      result = result + """
      <div><strong>{}-{} {}</strong><br/>
      {:0.1f}hr; {:0.1f}cr; Requisites: <em>{}</em><br/>{} (<em>{}</em>)</div>
      """.format(row['discipline'],
                 row['number'],
                 row['title'],
                 float(row['hours']),
                 float(row['credits']),
                 row['requisites'],
                 row['description'],
                 row['designation'])
  else:
    result = """
    <form method="post" action="">
      <legend for="institution">Institution: </legend>
      <input type="text" id="institution" name="institution" />
      <button type="submit">Please</button>
    <form>
    """
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
