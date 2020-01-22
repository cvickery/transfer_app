from pgconnection import PgConnection
conn = PgConnection()
cursor = conn.cursor()
cursor.execute('select cip_code, cip_title from cip_codes')
_cip_codes = {cip.cip_code: cip.cip_title for cip in cursor.fetchall()}
conn.close()


def cip_codes(cip_code: str) -> str:
  while cip_code != '' and cip_code not in _cip_codes.keys():
    cip_code = cip_code[:-1]
  if cip_code != '':
    return _cip_codes[cip_code]
  return 'Unknown'
