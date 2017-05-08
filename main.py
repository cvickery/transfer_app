import logging
import sys

from flask import Flask, url_for, render_template, redirect, send_file

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

@app.route('/quickstart')
def quickstart():
  return render_template('quickstart.html')

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
