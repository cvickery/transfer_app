#! /usr/local/bin/python3
""" Manage the sequence of forms used for reviewing transfer rules.
"""
import os
import json
import uuid
import re

from datetime import datetime

from flask import render_template, Markup

import psycopg2
from psycopg2.extras import NamedTupleCursor

from app_header import header
from sendemail import send_token, send_message
from format_rules import institution_names, Source_Course, Destination_Course, Transfer_Rule, \
    format_rules

if os.getenv('DEVELOPMENT'):
  DEBUG = True
else:
  DEBUG = False


# do_form_0()
# =================================================================================================
def do_form_0(request, session):
  """
      No form submitted yet; generate the Form 1 page.
  """
  if DEBUG:
    print(f'*** do_form_0({session})')
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)

  cursor.execute("select count(*) from transfer_rules")
  num_rules = cursor.fetchone()[0]
  cursor.execute("select * from updates")
  updates = cursor.fetchall()
  rules_date = 'unknown'
  for update in updates:
    if update.table_name == 'transfer_rules':
      rules_date = datetime.fromisoformat(update.update_date)\
          .strftime('%B %e, %Y')
  cursor.close()
  conn.close()

  source_prompt = """
    <fieldset id="sending-field"><h2>Sending College(s)</h2>
    <div id="source-college-list">
    """
  n = 0
  for code in institution_names:
    n += 1
    source_prompt += """
        <div class='institution-select'>
          <input type="checkbox" name="source" class="source" id="source-{}" value="{}">
          <label for="source-{}">{}</label>
        </div>
    """.format(n, code, n, institution_names[code])
  source_prompt += """
  </div>
  <div>
    <button type="button" id="all-sources">Select All Sending Colleges</button>
    <button type="button"  id="no-sources">Clear All Sending Colleges</button>
    </div>
  </fieldset>
  """

  destination_prompt = """
    <fieldset id="receiving-field"><h2>Receiving College(s)</h2>
    <div id="destination-college-list">
    """
  n = 0
  for code in institution_names:
    n += 1
    destination_prompt += """
        <div class='institution-select'>
          <input type="checkbox" name="destination" class="destination" id="dest-{}" value="{}">
          <label for="dest-{}">{}</label>
        </div>
    """.format(n, code, n, institution_names[code])
  destination_prompt += """
    </div>
    <div>
    <button type="button" id="all-destinations">Select All Receiving Colleges</button>
    <button type="button"  id="no-destinations">Clear All Receiving Colleges</button>
    </div>
  </fieldset>
  """

  email = ''
  if 'email' in session:
    email = session['email']
  remember_me = ''
  if 'remember-me'in session:
    remember_me = 'checked="checked"'

  # Return Form 1
  result = f"""
    {header(title='Review Rules: Select Colleges',
            nav_items=[{'type': 'link',
            'href': '/',
            'text': 'Main Menu'}])}
    <DETAILS>
      <summary>
        Instructions
      </summary>
      <hr>
      <p>
        This is the first step for reviewing, and optionally commenting on, the {num_rules:,}
        existing course transfer rules at CUNY.
      </p>
      <p>
        To see just the rules you are interested in, start here by selecting exactly one sending
        college and at least one receiving college, or exactly one receiving college and one or more
        sending colleges.
        <br/>
        In the next step you will select just the discipline(s) you are interested in, and in the
        last step you will be able to review the rules that match your selections from the first two
        steps.
      </p>
      <p>
        Background information and <em>(much!)</em> more detailed instructions are available in the
        <a  target="_blank"
            rel="noopener noreferrer"
            href="https://docs.google.com/document/d/141O2k3nFCqKOgb35-VvHE_A8OV9yg0_8F7pDIw5o-jE">
            Reviewing CUNY Transfer Rules</a> document.
      </p>
    </details>
    <fieldset>
      <form method="post" action="#" id="form-1">
          {source_prompt}
          {destination_prompt}
        <fieldset>
          <h2>Your email address</h2>
          <p>
            To record your comments and suggestions concerning existing transfer rules, you need to
            supply a valid CUNY email address here for verification purposes.<br/>If you just want
            to view the rules, you can use a dummy address, such as <em>nobody@cuny.edu</em>.
          </p>
          <label for="email-text">Enter a valid CUNY email address:</label>
          <div>
            <input type="text" name="email" id="email-text" value="{email}"/>
            <div>
              <input type="checkbox" name="remember-me" id="remember-me" {remember_me}/>
              <label for="remember-me"><em>Remember me on this computer.</em></label>
            </div>
          </div>
          <div id="error-msg" class="error"> </div>
          <input type="hidden" name="next-function" value="do_form_1" />
          <div>
          <button type="submit" id="submit-form-1">Next (<em>select disciplines)</em></button>
          </div>
        </fieldset>
      </form>
    </fieldset>
    <hr>
    <div id="update-info">
      <p>CUNYfirst information last updated {rules_date}</p>
    </div>
    """
  response = render_template('review_rules.html',
                             title='Select Colleges',
                             result=Markup(result))

  return response


# do_form_1()
# =================================================================================================
def do_form_1(request, session):
  """
      1. Collect source institutions, destination institutions and user's email from Form 1, and add
      them to the session.
      2. Generate Form 2 to select discipline(s)
  """
  if DEBUG:
     print(f'*** do_form_1({session})')

  #  do_form_1: put form 1 info (source/destination colleges; users email) into the session
  #  dictionary.
  session['source_institutions'] = request.form.getlist('source')
  session['destination_institutions'] = request.form.getlist('destination')
  session['email'] = request.form.get('email')
  session['remember-me'] = request.form.get('remember-me') == 'on'
  # The session: does the user want her to persist?
  session.permanent = session['remember-me']

  # Database lookups
  # ----------------
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)

  # The CUNY Subjects table, for getting subject descriptions from their abbreviations
  cursor.execute("select * from cuny_subjects order by subject")
  subject_names = {row.subject: row.subject_name for row in cursor}

  # Generate table headings for source and destination institutions
  sending_is_singleton = False
  sending_heading = 'Sending Colleges’'
  receiving_is_singleton = False
  receiving_heading = 'Receiving Colleges’'
  criterion = ''
  if len(session['source_institutions']) == 1:
    sending_is_singleton = True
    criterion = 'the sending college is ' + institution_names[session['source_institutions'][0]]
    sending_heading = f"{institution_names[session['source_institutions'][0]]}’s".replace('s’s',
                                                                                          's’')
  if len(session['destination_institutions']) == 1:
    receiving_is_singleton = True
    receiving_heading = f"{institution_names[session['destination_institutions'][0]]}’s".replace(
        's’s', 's’')
    if sending_is_singleton:
      criterion += ' and '
    criterion += 'the receiving college is ' + \
        institution_names[session['destination_institutions'][0]]

  # Look up all {source_institution, source_discipline, cuny_subject}
  #         and {destination_institution, destination_discipline, cuny_subject}
  # tuples for the selected source and destination institutions.

  source_institution_params = ', '.join('%s' for i in session['source_institutions'])
  q = """
  select institution,
         '<span title="'||discipline_name||'">'||discipline||'</span>' as discipline,
         cuny_subject
     from cuny_disciplines
    where institution in ({})
    """.format(source_institution_params)
  cursor.execute(q, session['source_institutions'])
  source_disciplines = cursor.fetchall()

  destination_institution_params = ', '.join('%s' for i in session['destination_institutions'])
  q = f"""
  select institution,
         '<span title="'||discipline_name||'">'||discipline||'</span>' as discipline,
         cuny_subject
     from cuny_disciplines
    where institution in ({destination_institution_params})
    """
  cursor.execute(q, session['destination_institutions'])
  destination_disciplines = cursor.fetchall()
  cursor.close()
  conn.close()

  # do_form_1: generate form 2
  # -----------------------------------------------------------------------------------------------
  # The CUNY subjects actually used by the source and destination disciplines.
  cuny_subjects = set([d.cuny_subject for d in source_disciplines])
  cuny_subjects |= set([d.cuny_subject for d in destination_disciplines])
  cuny_subjects.discard('')  # empty strings don't match anything in the subjects table.
  cuny_subjects = sorted(cuny_subjects)

  # Build selection list. For each cuny_subject found in either sending or receiving disciplines,
  # list all disciplines for that subject, with checkboxes for selecting either the sending or
  # receiving side.
  # The user sees College: discipline(s) in the table (source_disciplines_str), and that info is
  # encoded as a colon-separated list of college-discipline pairs (source_disciplines_val) as the
  # value of the corresponding cbox. *** TODO *** and then parse the value in do_form_2() ***
  selection_rows = ''
  num_rows = 0
  for cuny_subject in cuny_subjects:

    # Sending College(s)’ Disciplines
    #   Both the college and discipline names will be displayed for each cuny_subject, unless there
    #   is only one college involved ("singleton"), in which case only the discipline name is shown.
    source_disciplines_str = ''
    source_disciplines_val = ''
    source_disciplines_set = set()
    for discipline in source_disciplines:
      if discipline.cuny_subject == cuny_subject:
        if sending_is_singleton:
          source_disciplines_set.add(discipline.discipline)
        else:
          source_disciplines_set.add((discipline.institution, discipline.discipline))
    source_disciplines_set = sorted(source_disciplines_set)

    if sending_is_singleton:
      if len(source_disciplines_set) > 1:
        source_disciplines_str = '<div>' + '</div><div>'.join(source_disciplines_set) + '</div>'
      else:
        source_disciplines_str = ''.join(source_disciplines_set)
    else:
      colleges = {}
      for discipline in source_disciplines_set:
        if discipline[0] not in colleges.keys():
          colleges[discipline[0]] = []
        colleges[discipline[0]].append(discipline[1])
      for college in colleges:
        source_disciplines_str += '<div>{}: <em>{}</em></div>'.format(institution_names[college],
                                                                      ', '.join(colleges[college]))

    # Receiving College Disciplines
    destination_disciplines_str = ''
    destination_disciplines_set = set()
    for discipline in destination_disciplines:
      if discipline.cuny_subject == cuny_subject:
        if receiving_is_singleton:
          destination_disciplines_set.add(discipline.discipline)
        else:
          destination_disciplines_set.add((discipline.institution, discipline.discipline))
    destination_disciplines_set = sorted(destination_disciplines_set)

    if receiving_is_singleton:
      destination_disciplines_str = ''
      if len(destination_disciplines_set) > 1:
        destination_disciplines_str = '<div>' + \
                                      '</div><div>'.join(destination_disciplines_set) + '</div>'
      else:
        destination_disciplines_str = ''.join(destination_disciplines_set)
    else:
      colleges = {}
      for discipline in destination_disciplines_set:
        if discipline[0] not in colleges.keys():
          colleges[discipline[0]] = []
        colleges[discipline[0]].append(discipline[1])
      for college in colleges:
        destination_disciplines_str += '<div>{}: <em>{}</em></div>'.\
            format(institution_names[college], ', '.join(colleges[college]))

    # We are showing disciplines, but reporting cuny_subjects.

    source_label = ''
    source_cbox = ''
    source_is_active = ''
    if source_disciplines_str != '':
      source_is_active = ' active-cell'
      source_label = f'<label for="source-subject-{cuny_subject}">{source_disciplines_str}</label>'
      source_cbox = f"""
        <label for="source-subject-{cuny_subject}">
          <input type="checkbox"
                 id="source-subject-{cuny_subject}"
                 name="source_subject"
                 value="{cuny_subject}"/> </label>"""

    destination_label = ''
    destination_cbox = ''
    dest_is_active = ''
    if destination_disciplines_str != '':
      dest_is_active = ' active-cell'
      destination_label = f"""
      <label for="destination-subject-{cuny_subject}">{destination_disciplines_str}</label>"""
      destination_cbox = f"""
        <label for="destination-subject-{cuny_subject}">
          <input  type="checkbox"
                  checked="checked"
                  id="destination-subject-{cuny_subject}"
                  name="destination_subject"
                  value="{cuny_subject}"/></label>
        """

    selection_rows += f"""
    <tr>
      <td class="source-subject{source_is_active}">{source_label}</td>
      <td class="source-subject f2-cbox{source_is_active}">{source_cbox}</td>
      <td><span title="{cuny_subject}">{subject_names[cuny_subject]}</span></td>
      <td class="destination-subject f2-cbox{dest_is_active}">{destination_cbox}</td>
      <td class="destination-subject{dest_is_active}">{destination_label}</td>
    </tr>
    """
    num_rows += 1

  shortcuts = """
              <h2 class="error">
                There are no disciplines that match the combination of colleges you selected.
              </h2>
              """
  if num_rows > 1:
    shortcuts = """
    <table id="f2-shortcuts">
    <tr>
      <td f2-cbox" colspan="2">
        <div>
          <label for="all-source-subjects"><em>Select All Sending Disciplines: </em></label>
          <input  type="checkbox"
                  id="all-source-subjects"
                  name="all-source-subjects" />
        </div>
        <div>
          <label for="no-source-subjects"><em>Clear All Sending Disciplines: </em></label>
          <input type="checkbox" id="no-source-subjects" checked="checked"/>
        </div>
      </td>
      <td f2-cbox" colspan="2">
        <div>
          <label for="all-destination-subjects"><em>Select All Receiving Disciplines: </em>
          </label>
          <input  type="checkbox"
                  id="all-destination-subjects"
                  name="all-destination-subjects"
                  checked="checked"/>
        </div>
        <div>
          <label for="no-destination-subjects"><em>Clear All Receiving Disciplines: </em></label>
          <input type="checkbox" id="no-destination-subjects" />
        </div>
      </td>
    </tr>
    </table>
    """

  # Return Form 2
  result = f"""
  {header(title='Review Rules: Select Disciplines',
          nav_items=[{'type': 'link',
          'href': '/',
          'text': 'Main Menu'},
          {'type': 'link',
           'href': '/review_rules',
           'text': 'Change Colleges'}])}
  <details>
  <summary>
    There are {len(source_disciplines) + len(destination_disciplines):,} disciplines where
    {criterion}.
  </summary>
  <hr>
  <p>
    Disciplines are grouped by CUNY subject area. Hover over abbreviations in the first and last
    columns for full names.
  </p>
  <p>
    Select at least one sending discipline and at least one receiving discipline.
  </p>
  <p>
    By default, all receiving disciplines are selected to account for all possible equivalencies,
    including electives and blanket credit.
  </p>
  <p>
    The next step will show all transfer rules for courses in the corresponding pairs of
    disciplines.
  </p>
  </details>
  <form method="post" action="#" id="form-2">
  <button id="submit-form-2" type="submit">Next <em>(View Rules)</em></button>
    <input type="hidden" name="next-function" value="do_form_2" />
    {shortcuts}
    <div id="subject-table-div" class="selection-table-div">
      <div>
        <table id="subject-table" class="scrollable">
          <thead>
            <tr>
              <th class="source-subject">{sending_heading} Discipline(s)</th>
              <th class="source-subject">Select Sending</th>
              <th>CUNY Subject</th>
              <th class="destination-subject">Select Receiving</th>
              <th class="destination-subject">{receiving_heading} Discipline(s)</th>
            </tr>
          </thead>
          <tbody>
          {selection_rows}
          </tbody>
        </table>
      </div>
    </div>
  </form>
  <div id='form-2-submitted'>
    Searching <span class='dot-1'>.</span> <span class='dot-2'>.</span> <span class='dot-3'>.</span>
  </div>
  """
  response = render_template('review_rules.html', result=Markup(result))
  return response


# do_form_2()
# =================================================================================================
def do_form_2(request, session):
  """
      Process CUNY Subject list from form 2.
      Generate form_3: the selected transfer rules for review
  """
  if DEBUG:
    print(f'*** do_form_2(session)')
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)

  # Look up transfer rules where the sending course belongs to a sending institution and is one of
  # the source disciplines and the receiving course belongs to a receiving institution and is one of
  # the receiving disciplines.
  try:
    source_institution_params = ', '.join('%s' for i in session['source_institutions'])
    destination_institution_params = ', '.join('%s' for i in session['destination_institutions'])
  except KeyError:
    # the session is expired or invalid. Go back to Step 1.
    return render_template('review_rules.html', result=Markup("""
                                                           <h1>Session Expired</h1>
                                                           <p>
                                                             <a href="/" class="button">
                                                                Main Menu</a>
                                                             <a href="/review_rules"
                                                                  class="restart button">Restart
                                                              </a>
                                                           </p>

                                                           """))

  # Be sure there is the possibility there will be some rules
  source_subject_list = request.form.getlist('source_subject')
  destination_subject_list = request.form.getlist('destination_subject')

  if len(source_subject_list) < 1:
    return render_template('review_rules.html', result=Markup(
                           '<h1 class="error">No sending disciplines selected.</h1>'))
  if len(destination_subject_list) < 1:
    return render_template('review_rules.html', result=Markup(
                           '<h1 class="error">No receiving disciplines selected.</h1>'))

  # Prepare the query to get the set of rules that match the institutions and cuny_subjects
  # selected.
  if request.form.get('all-source-subjects'):
    source_subjects_clause = ''
  else:
    source_subjects_str = '|'.join(f':{s}:' for s in source_subject_list)
    source_subjects_clause = f"  and '{source_subjects_str}' ~ source_subjects"
    source_subjects = ', '.join(f"'{s}'" for s in source_subject_list)
    source_subjects_clause = f"""
      and id in (select rule_id from subject_rule_map where subject in ({source_subjects}))"""

  # Get all the rules where,
  #  - The source and destination institutions have been selected
  #  and
  #  - The source_subjects have been selected
  q = f"""
  select *
    from transfer_rules
   where source_institution in ({source_institution_params})
     and destination_institution in ({destination_institution_params})
     {source_subjects_clause}
  order by source_institution, destination_institution, subject_area, group_number"""
  cursor.execute(q, (session['source_institutions'] + session['destination_institutions']))
  if cursor.rowcount < 1:
    return render_template('review_rules.html', result=Markup(
                           '<h1 class="error">There are no matching rules.</h1>'))

  all_rules = cursor.fetchall()
  selected_rules = []
  # Get the source and destination course lists from the above set of rules where the destination
  # subject was selected. It's possible to have selected rules that don’t transfer to any of the
  # selected destination subjects, so those rules are dropped while building the selected-rules
  # list.
  if request.form.get('all-destination-subjects'):
    destination_subjects_clause = ''
  else:
    # Create a clause that makes sure the destination course has one of the destination subjects
    destination_subject_list = request.form.getlist('destination_subject')
    destination_subject_params = ', '.join(f"'{s}'" for s in destination_subject_list)
    destination_subjects_clause = f" and dc.cuny_subject in ({destination_subject_params})"

  for rule in all_rules:
    # It’s possible some of the selected rules don’t have destination courses in any of the selected
    # disciplines, so that has to be checked first.
    cursor.execute(f"""
      select  dc.course_id,
              dc.offer_count,
              dc.discipline,
              dc.catalog_number,
              dc.cat_num,
              dc.cuny_subject,
              dc.transfer_credits,
              dn.discipline_name
      from destination_courses dc, cuny_disciplines dn
      where dc.rule_id = %s
        and dn.institution = %s
        and dn.discipline = dc.discipline
        {destination_subjects_clause}
       order by discipline, cat_num
    """, (rule.id, rule.destination_institution))
    if cursor.rowcount > 0:
      destination_courses = [Destination_Course._make(c) for c in cursor.fetchall()]
      cursor.execute("""
        select  sc.course_id,
                sc.offer_count,
                sc.discipline,
                sc.catalog_number,
                sc.cat_num,
                sc.cuny_subject,
                sc.min_credits,
                sc.max_credits,
                sc.min_gpa,
                sc.max_gpa,
                dn.discipline_name
        from source_courses sc, cuny_disciplines dn
        where sc.rule_id = %s
          and dn.institution = %s
          and dn.discipline = sc.discipline
        order by discipline, cat_num
        """, (rule.id, rule.source_institution))
      if cursor.rowcount > 0:
        source_courses = [Source_Course._make(c)for c in cursor.fetchall()]

      # Create the Transfer_Rule tuple suitable for passing to format_rules, and add it to the
      # list of rules to pass.
      selected_rules.append(Transfer_Rule._make(
          [rule.id,
           rule.source_institution,
           rule.destination_institution,
           rule.subject_area,
           rule.group_number,
           rule.source_disciplines,
           rule.source_subjects,
           rule.review_status,
           source_courses,
           destination_courses]))
  cursor.close()
  conn.close()

  if len(selected_rules) == 0:
    num_rules = 'No matching transfer rules found.'
  if len(selected_rules) == 1:
    num_rules = 'There is one matching transfer rule.'
  if len(selected_rules) > 1:
    num_rules = 'There are {:,} matching transfer rules.'.format(len(selected_rules))

  rules_table = format_rules(selected_rules, scrollable=True)

  result = f"""
  {header(title='Review Rules: Review Selected Rules',
          nav_items=[{'type': 'link',
          'href': '/',
          'text': 'Main Menu'},
          {'type': 'link',
           'href': '/review_rules',
           'text': 'Change Colleges'},
           {'type': 'button',
            'class': 'back-button',
            'text': 'Change Subjects'

           }])}
    <details>
      <summary>{num_rules}</summary>
      <hr>
      <p>
        Rules that are <span class="credit-mismatch">highlighted like this</span> have a different
        number of credits taken from the number of credits transferred.
        Hover over the “=>” to see the numbers of credits.
      </p>
      <p>
        Credits in parentheses give the number of credits transferred where that does not match the
        nominal number of credits for a course.
      </p>
      <p>
        Rules that are <span class="evaluated">highlighted like this</span> are ones that you have
        reviewed but not yet submitted.
      </p>
      <p>
        Click on a rule to review it.
      </p>
    </details>
    <fieldset id="verification-fieldset"><legend>Review Reviews</legend>
        <p id="num-pending">You have not reviewed any transfer rules yet.</p>
        <button type="text" id="send-email" disabled="disabled">
        Review Your Reviews
      </button>
      <form method="post" action="#" id="review-form">
        Waiting for rules to finish loading ...
      </form>
    </fieldset>
    <div id="rules-table-div" class="selection-table-div table-height">
    {rules_table}
    </div>
  """
  return render_template('review_rules.html', result=Markup(result))


# do_form_3()
# -------------------------------------------------------------------------------------------------
def do_form_3(request, session):
  if DEBUG:
      print('*** do_form_3({session})')
  reviews = json.loads(request.form['reviews'])
  kept_reviews = [e for e in reviews if e['include']]
  email = session['email']
  if len(kept_reviews) == 0:
    result = '<h1>There are no reviews to confirm.</h1>'
  else:
    message_tail = 'review'
    if len(kept_reviews) > 1:
      num_reviews = len(kept_reviews)
      if num_reviews < 13:
        num_reviews = ['', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
                       'eleven', 'twelve'][num_reviews - 1]
      message_tail = '{} reviews'.format(num_reviews)

    # Insert these reviews into the pending_reviews table of the db.
    conn = psycopg2.connect('dbname=cuny_courses')
    cursor = conn.cursor(cursor_factory=NamedTupleCursor)
    token = str(uuid.uuid4())
    reviews = json.dumps(kept_reviews)
    q = "insert into pending_reviews (token, email, reviews) values(%s, %s, %s)"
    cursor.execute(q, (token, email, reviews))
    conn.commit()
    conn.close()

    # Description message templates
    review_dict = dict()
    review_dict['ok'] = '{}: OK'
    review_dict['not-ok'] = '{}: {}'
    review_dict['other'] = 'Other: {}'

    # Generate description messages
    style_str = ' style="border:1px solid #666;vertical-align:middle; padding:0.5em;"'
    suffix = 's'
    if len(kept_reviews) == 1:
      suffix = ''
    review_rows = f"""
                    <table style="border-collapse:collapse;">
                      <tr>
                        <th colspan="5"{style_str}>Rule</th>
                        <th{style_str}>Your Review{suffix}</th>
                      </tr>
                      """
    for review in kept_reviews:
      print(review['rule_str'])
      event_type = review['event_type']
      if event_type == 'src-ok':
          description = review_dict['ok'].format(re.sub(r'\d+', '',
                                                        review['source_institution']))
      elif event_type == 'dest-ok':
        description = review_dict['ok'].format(re.sub(r'\d+', '',
                                                      review['destination_institution']))
      elif event_type == 'src-not-ok':
        description = review_dict['not-ok'].format(re.sub(r'\d+', '',
                                                          review['source_institution']),
                                                   review['comment_text'])
      elif event_type == 'dest-not-ok':
        description = review_dict['not-ok'].format(re.sub(r'\d+', '',
                                                          review['destination_institution']),
                                                   review['comment_text'])
      else:
        description = review_dict['other'].format(review['comment_text'])

      rule_str = re.sub('</tr>',
                        f'<td>{description}</td></tr>', review['rule_str'])
      review_rows += re.sub('<td([^>]*)>', f'<td\\1{style_str}>', rule_str)
    review_rows += '</table>'

    # Send the email
    hostname = os.environ.get('HOSTNAME')
    if hostname and hostname.endswith('.local'):
      hostname = 'http://localhost:5000'
    else:
      hostname = 'https://transfer-app.qc.cuny.edu'
    url = hostname + '/confirmation/' + token

    response = send_token(email, url, review_rows)
    if response.status_code != 202:
      result = f'Error sending email: {response.body}'
    else:
      result = f"""
      {header(title='Review Rules: Respond to Email',
              nav_items = [
              {'type': 'link',
               'href': '/',
               'text': 'Main Menu'},
              {'type': 'link',
               'href': '/review_rules',
               'text':'Review More Rules'}])}
      <details>
        <summary>Check your email at {email}</summary>
        <hr>
        <p>
          Click on the 'activate these reviews' button in that email
          to confirm that you actually wish to have your {message_tail} recorded.
        </p>
      </details>
      <h2>
        Thank you for your work!
      </h2>
      """
  return render_template('review_rules.html', result=Markup(result))
