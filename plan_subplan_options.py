#! /usr/local/bin/python3
""" Provide dicts of html <option> elements for the plans and subplans
    by institution.
    f'<optgroup label="{block_type}"'
    f'<option value="{block_value}">{block_title} {requirement_id}</option>'
"""
import psycopg

from psycopg.rows import namedtuple_row

options_dict = dict()
nice_names = {'MAJOR': 'Majors',
              'MINOR': 'Minors',
              'CONC': 'Concentrations',
              'DEGREE': 'Degrees',
              'OTHER': 'Others'}

with psycopg.connect('dbname=cuny_curriculum') as conn:
  with conn.cursor(row_factory=namedtuple_row) as cursor:
    cursor.execute("""
    select institution, requirement_id, block_type, block_value, title as block_title
      from requirement_blocks
           -- This join with ordinality is postgres-talk for controlling the order of results
           join unnest(array['MAJOR','CONC','MINOR', 'DEGREE', 'OTHER']::text[])
            with ordinality t(block_type, ord) using (block_type)
     where term_info is not null
    order by institution, t.ord, block_value
    """)
    last_institution = None
    last_block_type = None
    for row in cursor:
      institution, requirement_id, block_type, block_value, block_title = row
      if (this_institution := institution[0:3]) != last_institution:
        options_dict[this_institution] = {'options_list': [],
                                          'requirement_ids': []
                                          }
        if last_institution is not None:
          options_dict[last_institution]['options_html'] = '\n'.join(options_dict[last_institution]['options_list'])
        last_institution = this_institution
        last_block_type = None

      if (block_type := row.block_type) != last_block_type:
        try:
          nice_name = nice_names[block_type]
        except KeyError:
          nice_name = block_type

        options_dict[this_institution]['options_list'].append(f'<optgroup label="{nice_name}">')
        last_block_type = block_type
      options_dict[this_institution]['options_list'].append(f'<option value="{block_value}">'
                                                            f'{block_title} '
                                                            f'{requirement_id}</option>')

if __name__ == '__main__':
  institution, requirement_id = input('College RA? ').split()
  print(f'{institution[0:3].upper()}01', f"RA{int(requirement_id.upper().strip('RA')):06}")
