#! /usr/local/bin/python3

from pgconnection import pgconnection

from format_rules import institution_names

db = pgconnection()
cursor = db.cursor()
cursor.execute('select * from institutions')


def _propose_rules():
  """ Return a form for proposing a new transfer rule. With the aid of JavaScript, multiple rules
      can be proposed.
      For each rule, the provosts and registrars of both colleges involved are notified.
  """
  institution_options = '\n'.join([f'<option value="{k}">{institution_names[k]}</option>'
                                  for k in institution_names.keys()])
  result = f"""
  <form action="#" method="post">
    <fieldset><legend>Edit Rule</legend>
      <label for="src-institution">Sending College</label>
      <select name="src-institution" id="src_institution">{institution_options}</select>
      <label for="dst-institution">Receiving College</label>
      <select name="dst-institution" id="dst_institution">{institution_options}</select>
      <hr>
      <label for="src-disciplines">Sending Discipline</label>
      <select name="src-discipline" id="src-discipline"></select>
    </fieldset>
    <div id="prepared-rules">
    </div>
  </form>
  """
  return result
