#! /usr/local/bin/python3
""" Generate list of rules to evaluate without need to do so much navigation/selection.
"""

from collections import namedtuple, defaultdict

from app_header import header

from format_rules import format_rule_by_key
from pgconnection import PgConnection

"""
    The idea is to skip the "select disciplines" form by knowing the reviewer's email.
    They still have to pick the other college(s) involved
    Get email; look up their college, department, and name
      If not in person_roles table, send them to longcut form
      If associate's college, assume sending rules
      If bachelor's college, assume receiving rules
      If both, ask which way
      (Multi?)select college(s) of interest
      Limit to BKCR?
      Include MESG?

    Heuristic: Look at rules where the sending/receiving course is person's discipline instead of
    searching by cuny_subject.
    Heuristic: Look at rules for courses most-frequently transferred.
"""
Role = namedtuple('Role', 'role institution organization')
Course = namedtuple('Course', 'course_id offer_nbr discipline catalog_number title is_bkcr is_mesg')


def shortcut_to_rules(request, session):
  """ Given a user's email address, see if they are in the person_roles table, and if so generate
      a quick list of rule keys based on some simple additional info.
  """
  for key in session.keys():
    print(f'{key}: {session[key]}')
  remember_me = session['remember_me']

  # session.clear()

  conn = PgConnection()
  cursor = conn.cursor()

  # Determine user
  email = None
  email_prompt = 'Your CUNY email address'
  old_value = ''
  while email is None:
    if 'email' in request.form:
      # Request Form overrides session
      email = request.form.get('email')
      if email.lower().endswith('@cuny.edu') or email.lower().endswith('.cuny.edu'):
        session['email'] = request.form.get('email')
        session['remember_me'] = request.form.get('remember_me') == 'on'
        remember_me = session['remember_me']
      else:
        old_value = email
        email = None
        email_prompt = 'CUNY email addresses end with “cuny.edu”'

    elif 'email' in session:
      email = session['email']

    else:
      old_value = ''
      email = None
      email_prompt = 'Your CUNY email address'

    if email:
      cursor.execute("""
      select name, email from people where email ~* %s or alternate_emails ~* %s
      """, (email, email))
      if cursor.rowcount == 1:
        row = cursor.fetchone()
        name, email = row.name, row.email
        # Get roles
        cursor.execute("""
        select role, institution, organization from person_roles where email ~ %s
        """, (email, ))
        if cursor.rowcount == 0:
          old_value = email
          email = None
        else:
          roles = [Role(row.role, row.institution, row.organization) for row in cursor.fetchall()]
          print(f'{roles=}')
      else:
        # Unrecognized (rowcount = 0) or Ambiguous (rowcount > 1) Email
        email = None
        email_prompt = ('Unrecognized email address. Change it, or '
                        '<a href="/review_rules/">Use This Link</a>')

    if email is None:
      # Get user’s (fixed) email and come back here with it.
      email_form = f"""
        <h1>Your CUNY email address, please.</h1>
        <fieldset><legend>{email_prompt}</legend>
          <form method='POST', action='/quick_rules/'>
            <label for="email">Email</label> <input type="text"
                                                    id="email"
                                                    name="email"
                                                    value="{old_value}"
                                                    size="30"/>
            <button type="submit">Submit</button><br>
            <label for="remember-me">Remember Me</label> <input type="checkbox"
                                                                name="remember_me"
                                                                value="{remember_me}"
                                                                id="remember-me"/>
          </form>
        </fieldset
    """
      conn.close()
      return email_form

  debug = f'<h2>{name}</h2>'

  # Got email, name, and non-empty list of roles. Which rules to review?
  """ If provost and evaluator ask which role (not yet)
      If user role includes evaluator
        Community college: all active sending courses from organization's subjects, ordered by
        frequency of transfer and BKCR-ness at receiving end. Note missing rules.
        Senior college: all receiving courses from organization's subjects, ordered by frequency of
        transfer.
      If user role includes provost (not yet)
      Else send to longcut interface
  """
  for role in roles:
    if role.role == 'webmaster':
      pass
    elif role.role == 'evaluator':
      debug += '<p>Hello Evaluator!</p>'
      cursor.execute(f"""
      select associates, bachelors from cuny_institutions
      where code = '{role.institution}'
      """)
      assert cursor.rowcount == 1
      row = cursor.fetchone()
      is_receiving = row.bachelors
      is_sending = row.associates
      cursor.execute(f"""
      select * from cuny_disciplines
      where institution = '{role.institution}'
        and department = '{role.organization}'
        and status = 'A'
      """)
      assert cursor.rowcount > 0
      disciplines = [row.discipline for row in cursor.fetchall()]
      debug += f'<p>{is_sending=} {is_receiving=} {disciplines=}</p>'

      # Get all course_ids for all disciplines so we can report missing rules
      discipline_list = ', '.join(f"'{d}'" for d in disciplines)
      cursor.execute(f"""
      select course_id, offer_nbr, discipline, catalog_number, title,
             designation in ('MLA', 'MNL') as is_mesg,
             attributes ~ 'BKCR' as is_bkcr
        from cuny_courses
       where institution = '{role.institution}'
         and discipline in ({discipline_list})
         and course_status = 'A'
       order by discipline, numeric_part(catalog_number)
      """)
      assert cursor.rowcount > 0
      courses = {r.course_id: Course(r.course_id, r.offer_nbr, r.discipline, r.catalog_number,
                                     r.title, r.is_bkcr, r.is_mesg)
                 for r in cursor.fetchall() if is_sending or is_receiving and r.is_bkcr}
      debug += f'<p>{courses=}</p>'

      # Get counts of how many times each course_id transferred
      trans_conn = PgConnection('cuny_transfers')
      trans_cursor = trans_conn.cursor()
      course_id_list = ','.join(f'{courses[k].course_id}' for k in courses.keys())
      if is_receiving:
        trans_cursor.execute(f"""
        select count(*), dst_course_id as course_id
          from transfers_applied
         where dst_course_id in ({course_id_list})
          group by dst_course_id
          order by count desc
        """)
        cursor.execute(f"""
        select rule_key(rule_id), array_agg(course_id) as course_ids
          from transfer_rules r, destination_courses
         where course_id in ({course_id_list})
           group by rule_id
        """)
      if is_sending:
        trans_cursor.execute(f"""
        select count(*), src_course_id as course_id
          from transfers_applied
         where src_course_id in ({course_id_list})
         group by src_course_id
         order by count desc
        """)
        cursor.execute(f"""
        select rule_key(rule_id), array_agg(course_id) as course_ids
          from source_courses
         where course_id in ({course_id_list})
           group by rule_id
        """)
      xfer_course_counts = defaultdict(int)
      for r in trans_cursor.fetchall():
        xfer_course_counts[int(r.course_id)] = int(r.count)
      rule_keys = defaultdict(int)
      for rule in cursor.fetchall():
        course_ids = set([int(id) for id in rule.course_ids])
        for course_id in course_ids:
          rule_keys[rule.rule_key] = course_id

      debug += f'<p>{xfer_course_counts=}/</p>'
      debug += f'<p>{rule_keys=}</p>'
    else:
      debug += f'<p>{role.role.title()} Role not implmented yet</p>'
  eval_table = """
  <table id="eval-table">
    <tr>
      <th>Sending<br>College</th><th>Sending<br>Courses</th><th>Credits<br>Transferred</th>
      <th>Receiving<br>College</th><th>Receiving<br>Courses</th><th>Review<br>Status</th>
    </tr>
  """
  for rule_key in rule_keys.keys():
    row, text = format_rule_by_key(rule_key)
    eval_table += row
  eval_table += '</table>'
  result = f"""
  {header(title='Quick Access To Rules',
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
    <details open>
      <summary>Instructions (click to open/close)</summary>
      <hr>
      <p>
        Here are {len(rule_keys):,} rules where a course transfers as Blanket Credit.
      </p>
      </details>
    {eval_table}

"""
  cursor.close()
  trans_cursor.close()
  return result

  # Generate list of rule_keys
  if len(selected_rules) == 0:
    num_rules = 'No matching transfer rules found.'
  if len(selected_rules) == 1:
    num_rules = 'There is one matching transfer rule.'
  if len(selected_rules) > 1:
    num_rules = f'There are {len(selected_rules):,} matching transfer rules.'

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
    <details open>
      <summary>Instructions (click to open/close)</summary>
      <hr>
      {num_rules}
      <p>
      Blanket Credit courses are <span class="blanket">highlighted like this</span>.
      </p>
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
      <p class="call-to-action">
        Click on a rule to review it
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
