import logging
import sys
import os

import json
import uuid
import datetime
import sqlite3

import logging

from collections import namedtuple

from cuny_course import CUNYCourse
from mysession import MySession

from flask import Flask, url_for, render_template, make_response,\
                  redirect, send_file, Markup, request, jsonify

app = Flask(__name__)
app.secret_key = os.urandom(24)

# email server
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

# administrator list
ADMINS = ['your-gmail-username@gmail.com']

#
# Initialization

Filter = namedtuple('Filter', ['subject', 'college', 'discipline'])

logger = logging.getLogger('debugging')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('debugging.log')
sh = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
#logger.addHandler(fh)
logger.addHandler(sh)
logger.debug('Debug: App Start')
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

#   NOTE TO SELF: See http://flask.pocoo.org/docs/0.12/patterns/jquery/ when you want to do ajax to
#   get catalog descriptions


# do_form_0()
# -------------------------------------------------------------------------------------------------
def do_form_0(request, session):
  """
      No form submitted yet; generate the Step 1 page.
      Display form_1 to get aource and destination institutions; user's email.
  """
  logger.debug('do_form_0({})'.format(session))
  conn = sqlite3.connect('static/db/cuny_catalog.db')
  conn.row_factory = sqlite3.Row
  c = conn.cursor()
  c.execute("select * from institutions order by lower(name)")
  institution_list = c.fetchall()

  source_prompt = """
    <fieldset id="sending-field"><legend>Sending College(s)</legend>
    <div id="source-college-list">
    """
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
  </div>
  <div>
    <button type="button" id="all-sources">Select All Sending Colleges</button>
    <button type="button"  id="no-sources">Clear All Sending Colleges</button>
    </div>
  </fieldset>
  """

  destination_prompt = """
    <fieldset id="receiving-field"><legend>Receiving College(s)</legend>
    <div id="destination-college-list">
    """
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
    </div>
    <div>
    <button type="button" id="all-destinations">Select All Receiving Colleges</button>
    <button type="button"  id="no-destinations">Clear All Receiving Colleges</button>
    </div>
  </fieldset>
  """
  destination_disciplines_prompt = "<fieldset><legend>Discipline/Subject(s)</legend>"
  destination_disciplines_prompt += "</fieldset>"

  email = ''
  if request.cookies.get('email') != None:
    email = request.cookies.get('email')
  remember_me = ''
  if request.cookies.get('remember-me') != None:
    remember_me = 'checked="checked"'

  # Return Form 1
  result = """
    <h1>Step 1: Select Colleges</h1>
    <p>
      This is the first step of a web application for reviewing course transfer rules at CUNY.<br/>
      Background information and instuctions are available in the
      <a
        href="https://docs.google.com/document/d/141O2k3nFCqKOgb35-VvHE_A8OV9yg0_8F7pDIw5o-jE/edit?usp=sharing">
        CUNY Transfer Rules Evaluation</a> document.
    <fieldset>
      <form method="post" action="" id="form-1">
          {}
          {}
        <fieldset>
          <legend>Your email address</legend>
          <label for="email-text">Enter a valid CUNY email address:</label>
          <div>
            <input type="text" name="email" id="email-text" value="{}"/>
            <div>
              <input type="checkbox" name="remember-me" id="remember-me" {}/>
              <label for="remember-me"><em>Remember me on this computer.</em></label>
            </div>
          </div>
          <div>
            <div id="error-msg" class="error"> </div>
            <input type="hidden" name="next-function" value="do_form_1" />
            <button type="submit" id="submit-form-1">Next</button>
          </div>
        </fieldset>
      </form>
    </fieldset>
    """.format(source_prompt, destination_prompt, email, remember_me)

  response = make_response(render_template('transfers.html', result=Markup(result)))
  response.set_cookie('mysession',
                      session.session_key)

  return response

# do_form_1()
# -------------------------------------------------------------------------------------------------
def do_form_1(request, session):
  """
      Collect source institutions, destination institutions and user's email from Form 1, and add
      them to the session.
      Generate Form 2: select discipline(s)
  """
  logger.debug('do_form_1({})'.format(session))
  # Capture form data in user's session
  session['source_institutions'] = request.form.getlist('source')
  session['destination_institutions'] = request.form.getlist('destination')

  # Get filter info
  conn = sqlite3.connect('static/db/cuny_catalog.db')
  conn.row_factory = sqlite3.Row
  c = conn.cursor()

  # Get source and destination institiution names
  c.execute("select * from institutions order by code")
  institution_names = {row['code']: row['name'] for row in c}

  # Look up all the rules for the source and destination institutions
  source_institution_list = "('" + "', '".join(session['source_institutions']) + "')"
  destination_institution_list = "('" + "', '".join(session['destination_institutions']) + "')"
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
  #   This gives a set of institution:discipline pairs for each subject
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
  # session['source_subjects'] = [source_subject for source_subject in source_subjects]
  # session['destination_subjects'] = [destination_subject for destination_subject in destination_subjects]

  sending_is_singleton = False
  sending_heading = 'Sending Colleges’'
  receiving_is_singleton = False
  receiving_heading ='Receiving Colleges’'
  criterion = ''
  if len(session['source_institutions']) == 1:
    sending_is_singleton = True
    criterion = 'the sending college is ' + institution_names[session['source_institutions'][0]]
    sending_heading = '{}’s'.format(institution_names[session['source_institutions'][0]])
  if len(session['destination_institutions']) == 1:
    receiving_is_singleton = True
    receiving_heading = '{}’s'.format(institution_names[session['destination_institutions'][0]])
    if sending_is_singleton: criterion += ' and '
    criterion += 'the receiving college is ' + institution_names[session['destination_institutions'][0]]

  c.execute("select * from cuny_subjects")
  cuny_subjects = {row['area']:row['description'] for row in c}

  c.execute("select * from careers")
  careers = {(row['institution'], row['career']): row['description'] for row in c}

  c.execute("select * from designations")
  designations = {row['designation']: row['description'] for row in c}

  # Build filter table. For each cuny_subject found in either sending or receiving courses, list
  # all disciplines at those colleges.
  # tuples are cuny_subject, college, discipline
  source_filters = set()
  destination_filters = set()
  for rule in rules:
    source_filters.add(Filter(rule.source_subject,
                              rule.source_institution,
                              rule.source_discipline))
    destination_filters.add(Filter(rule.destination_subject,
                                   rule.destination_institution,
                                   rule.destination_discipline))
  # Pass these filters on in the session
  session['source_filters'] = [filter for filter in source_filters]
  session['destination_filters'] = [filter for filter in destination_filters]

  # Table rows with checkboxes for subjects
  all_subjects = set([filter.subject for filter in source_filters])
  all_subjects |= set([filter.subject for filter in destination_filters])
  all_subjects = sorted(all_subjects)
  filter_rows = ''
  for cuny_subject in all_subjects:
    # Sending College Disciplines
    source_disciplines = ''
    source_discipline_set = set()
    for filter in source_filters:
      if filter.subject == cuny_subject:
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
      if filter.subject == cuny_subject:
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

    source_box = ''
    if source_disciplines != '':
      source_box = """
        <input type="checkbox" id="source-subject-{}" name="source_subject" value="{}"/>
        """.format(cuny_subject, cuny_subject)
    destination_box = ''
    if destination_disciplines != '':
      destination_box = """
        <input type="checkbox" id="destination-subject-{}" name="destination_subject" value="{}"/>
        """.format(cuny_subject, cuny_subject)
    filter_rows += """
    <tr>
      <td class="source-subject"><label for="source-subject-{}">{}</label></td>
      <td class="source-subject f2-cbox">{}</td>
      <td><strong>{}</strong></td>
      <td class="destination-subject"><label for="destination-subject-{}">{}</label></td>
      <td class="destination-subject f2-cbox">{}</td>
    </tr>
    """.format(cuny_subject,
               source_disciplines,
               source_box,
               cuny_subjects[cuny_subject],
               cuny_subject,
               destination_disciplines,
               destination_box)

  if len(all_subjects) > 1:
    shortcuts = """
    <tr>
      <td class="source-subject f2-cbox" colspan="2">
        <div>
          <label for="all-sending-subjects"><em>Select All Sending Subjects: </em></label>
          <input type="checkbox" id="all-sending-subjects{}" />
        </div>
        <div>
          <label for="no-sending-subjects"><em>Clear All Sending Subjects: </em></label>
          <input type="checkbox" id="no-sending-subjects{}" />
        </div>
      </td>
      <td> </td>
      <td class="destination-subject f2-cbox" colspan="2">
        <div>
          <label for="all-receiving-subjects"><em>Select All Receiving Subjects: </em></label>
          <input type="checkbox" id="all-receiving-subjects{}" />
        </div>
        <div>
          <label for="no-receiving-subjects"><em>Clear All Receiving Subjects: </em></label>
          <input type="checkbox" id="no-receiving-subjects{}" />
        </div>
      </td>
    </tr>
    """
    filter_rows = shortcuts.format('-top', '-top', '-top', '-top') + \
                  filter_rows + \
                  shortcuts.format('-bot', '-bot', '-bot', '-bot')

  # set or clear email-related cookes based on form data
  email = request.form.get('email')
  session['email'] = email # always valid for this session
  logger.debug('session[email] is {}'.format(session['email']))
  # The email cookie expires now or later, depending on state of "remember me"
  expire_time = datetime.datetime.now()
  remember_me = request.form.get('remember-me')
  if remember_me == 'on':
    expire_time = expire_time + datetime.timedelta(days=90)

  result = """
  <h1>Step 2: Select CUNY Subjects</h1>
  <form method="post" action="" id="form-2">
    <fieldset>
      <div>There are {:,} transfer rules where {}.</div>
      <a href="" class="restart">Restart</a>
      <button type="submit">Next</button>
      <table id="subject-filters">
        <tr>
          <th class="source-subject">{} Discipline(s)</th>
          <th class="source-subject">Select Sending</th>
          <th>CUNY Subject</th>
          <th class="destination-subject">{} Discipline(s)</th>
          <th class="destination-subject">Select Receiving</th>
        </tr>
        {}
      </table>
      <a href="" class="restart">Restart</a>
      <input type="hidden" name="next-function" value="do_form_2" />
      <button type="submit">Next</button>
    </fieldset>
  </form>
  """.format(len(rules), criterion, sending_heading, receiving_heading, filter_rows)

  response = make_response(render_template('transfers.html', result=Markup(result)))
  response.set_cookie('email', email, expires=expire_time)
  response.set_cookie('remember-me', 'on', expires=expire_time)

  return response

# do_form_2()
# -------------------------------------------------------------------------------------------------
def do_form_2(request, session):
  """
      Process CUNY Subject list from form 2 and add to session.
      Generate form_3: the selected transfer rules for evaluation
  """
  logger.debug('do_form_2({})'.format(session))
  conn = sqlite3.connect('static/db/cuny_catalog.db')
  conn.row_factory = sqlite3.Row
  c = conn.cursor()

  # Look up transfer rules where the sending course belongs to a sending institution and is one of
  # the source subjects and the receiving course blongs to a receiving institution and is one of
  # the receiving subjects.
  try:
    source_institution_list = "('" + "', '".join(session['source_institutions']) + "')"
    destination_institution_list = "('" + "', '".join(session['destination_institutions']) + "')"
  except:
    # the session is expired or invalid. Got back to Step 1.
    return render_template('transfers.html', result=Markup('{}'.format(session)))
  source_subjects = [subject for subject in request.form.getlist('source_subject')]
  destination_subjects = [subject for subject in request.form.getlist('destination_subject')]
  source_subject_list = "('" + "', '".join(source_subjects)      + "')"
  destination_subject_list = "('" + "', '".join(destination_subjects) + "')"
  q = """
  select  t.source_course_id,                                 -- 0 id
          i1.prompt as source_institution,                    -- 1 institution
          c1.discipline||'-'||c1.number as source_course,     -- 2 course

          t.destination_course_id,                            -- 3 id
          i2.prompt as destination_institution,               -- 4 institution
          c2.discipline||'-'||c2.number as destination_course -- 5 course
   from   transfer_rules t, courses c1, courses c2, institutions i1, institutions i2
  where
          c1.institution in {}
      and c1.cuny_subject in {}
      and c2.institution in {}
      and c2.cuny_subject in {}
      and c1.course_id = t.source_course_id
      and c2.course_id = t.destination_course_id
      and i1.code = c1.institution
      and i2.code = c2.institution
    order by lower(source_institution), source_course,
             lower(destination_institution), destination_course
  """.format(source_institution_list,
             source_subject_list,
             destination_institution_list,
             destination_subject_list)
  c.execute(q)
  rules = c.fetchall()
  if rules == None: rules = []

  # Rule ids: source_course_id:source_institution:dest_course_id:dest_institution
  the_list = '<table id="rules-table">'
  for rule in rules:
    the_list += """
    <tr id="{}" class="rule">
      <td>{}</td><td title="course id: {}">{}</td>
      <td>=></td>
      <td>{}</td><td title="course id: {}">{}</td>
    </tr>""".format(str(rule[0]) + ':' + rule[1] + ':' + str(rule[3]) + ':' + rule[4],
                    rule[1], rule[0], rule[2], rule[4], rule[3], rule[5])
  the_list += '</table>'
  num_rules = 'are no transfer rules'
  if len(rules) == 1: num_rules = 'is one transfer rule'
  if len(rules) > 1: num_rules = 'are {:,} transfer rules'.format(len(rules))
  result = """
  <h1>Step 3: Review Transfer Rules</h1>
  <fieldset id="rules-fieldset">
    <div>There {} selected.</div>
    <fieldset id="verification-fieldset">
    <p>
      There <span id="num-pending">are no evaluations</span> pending verification.
      <span id="verification-details"><br/>You will need to respond to an email we will send to your
      CUNY email account in order for your evaluations to be recorded.
      </span>
    </p>
    <button type="text" id="send-email" disabled="disabled">
      Review your evaluations before sending verification email to <em id="email-address">{}</em>.
    </button>
  </fieldset>
  <p>Click on a rule to evaluate it.</p>
    <form method="post" action="" id="evaluation-form">
      Please wait for rules to finish loading ...
    </form>
    {}
  </fieldset>
  <a href="" class="restart">Restart</a>
  """.format(num_rules,
             session['email'],
             the_list)
  return render_template('transfers.html', result=Markup(result))

# do_form_3()
# -------------------------------------------------------------------------------------------------
def do_form_3(request, session):
  logger.debug('do_form_3({})'.format(session))
  evaluations = json.loads(request.form['evaluations'])
  kept_evaluations = [evaluation for evaluation in evaluations if not evaluation['is_omitted']]
  email = session['email']
  if len(kept_evaluations) == 0:
    result = '<h1>There are no evaluations to confirm.</h1>'
  else:
    message_tail = 'evaluation'
    if len(kept_evaluations) > 1:
      count = len(kept_evaluations)
      if count < 13:
        count = ['two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
                'eleven', 'twelve'][count - 2]
      message_tail = '{} evaluations'.format(count)
    # Insert these evaluations into the pending_evaluations table.
    token = str(uuid.uuid4())
    evaluations = json.dumps(kept_evaluations)
    q = "insert into pending_evaluations (token, evaluations) values(?, ?)"
    conn = sqlite3.connect('static/db/cuny_catalog.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(q, (token, evaluations))
    conn.commit()
    # Send email with the token for verification
    #
    result = """
    <h1>Step 4: Respond to Email</h1>
    <p>
      We have sent an email to {}. Click on the 'Confirm' button in that email to confirm that you
      actually wish to submit your {}.
    </p>
    <p class="error">Under development: no email actually sent.</p>
    <p>
      Thank you for your work!
    </p>
    """.format(email, message_tail)
  return render_template('transfers.html', result=Markup(result))

# TRANSFERS PAGE
# =================================================================================================
#
@app.route('/transfers/', methods=['POST', 'GET'])
def transfers():
  """ (Re-)establish user's mysession and dispatch to appropriate function depending on which form,
      if any, the user submitted.
  """
  logger.debug('*** {} /transfers/ ***'.format(request.method))
  logger.debug(request.headers)
  mysession = MySession(request.cookies.get('mysession'))

  logger.debug('Pre-dispatch: mysession_key] is {}'.format(mysession.session_key))
  logger.debug('Pre-dispatch: mysession is {}'.format(mysession))

  # Dispatcher for forms
  dispatcher = {
    'do_form_1': do_form_1,
    'do_form_2': do_form_2,
    'do_form_3': do_form_3,
  }
  if request.method == 'POST':
    # User has submitted a form.
    logger.debug('dispatcher will call {}'.format(request.form['next-function']))
    return dispatcher.get(request.form['next-function'], lambda: error)(request, mysession)

  # Form not submitted yet, so call do_form_0 to generate form_1
  else:
    return do_form_0(request, mysession)

# /_COURSE
# =================================================================================================
# This route is for AJAX access to course catalog information.
@app.route('/_course')
def _course():
  course_id = request.args.get('course_id', 0)
  course = CUNYCourse(course_id)
  note = '<div class="warning"><strong>Note:</strong> Course is not active in CUNYfirst</div>'
  if course.is_active:
    note = ''
  return jsonify({'course_id': course.course_id,
                 'institution': course.institution,
                 'department': course.department,
                 'html': course.html,
                 'note': note})

# /_SESSIONS
# =================================================================================================
# This route is intended as a utility for pruning dead "mysessiob" entries from the db. A periodic
# script can access this url to prevent db bloat when millions of people start using the app. Until
# then, it's just here in case it's needed.
@app.route('/_sessions')
def _sessions():
  conn = sqlite3.connect('static/db/cuny_catalog.db')
  conn.row_factory = sqlite3.Row
  c = conn.cursor()
  c.execute('pragma foreign_keys = 1') # NOTE TO SELF FOR DOING INSERTS LATER
  q = 'select session_key, expiration_time from sessions'
  c.execute(q)
  result = '<table>'
  now = datetime.datetime.now()
  num_expired = 0
  for row in c.fetchall():
    ts = datetime.datetime.fromtimestamp(row['expiration_time'])
    ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
    status = 'active'
    if ts < now:
      status = 'expired'
      num_expired += 1
    result += '<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(row['session_key'],
                                                                  ts_str,
                                                                  status)
  msg = '<p>There were no expired sessions to delete.</p>'
  if num_expired > 0:
    c.execute("delete from sessions where expiration_time < {}".format(now.timestamp()))
    conn.commit()
    if num_expired == 1: msg = '<p>Deleted one expired session.</p>'
    else: msg = '<p>Deleted {} expired sessions.</p>'.format(num_expired)
  return result + '</table>' + msg

# COURSES PAGE
# =================================================================================================
# Pick a college, and see catalog descriptions of all courses currently active there.
@app.route('/courses/', methods=['POST', 'GET'])
def courses():
  num_courses = 0
  if request.method == 'POST':
    conn = sqlite3.connect('static/db/cuny_catalog.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("select * from cuny_subjects")
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
        select count(*) from courses
         where institution = '{}'
           and course_status = 'A'
           and can_schedule = 'Y'
           and discipline_status = 'A'
        """.format(institution_code)).fetchone()[0]

    result = """
      <h1>{} Courses</h1><p class='subtitle'>{:,} active courses as of {}</p>
      """.format(institution_name, num_active_courses, date_updated)

    query = """
      select * from courses
       where institution = '{}'
         and course_status = 'A'
         and can_schedule = 'Y'
         and discipline_status = 'A'
       order by discipline, number
       """.format(institution_code)
    c.execute(query)

    for row in c:
      num_courses += 1
      result = result + """
      <p class="catalog-entry"><strong>{} {}: {}</strong> (<em>{}; {}: {}</em>)<br/>
      {:0.1f}hr; {:0.1f}cr; Requisites: <em>{}</em><br/>{} (<em>{}</em>)</p>
      """.format(row['discipline'],
                 row['number'].strip(),
                 row['title'],
                 careers[(row['institution'],row['career'])],
                 row['cuny_subject'], cuny_subjects[row['cuny_subject']],
                 float(row['hours']),
                 float(row['credits']),
                 row['requisites'],
                 row['description'],
                 designations[row['designation']])

  # Form not submitted yet or institution has no courses
  if num_courses == 0:
    prompt = '<fieldset><legend>Select a College</legend>'
    conn = sqlite3.connect('static/db/cuny_catalog.db')
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
