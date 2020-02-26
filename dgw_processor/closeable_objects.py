#! /usr/local/bin/python3
""" Convert a Python data structure to an HTML structure that can be opened/collapsed to reveal/hide
    nested parts.

    There is a lot of overhead to make the generated html properly indented. This was for debugging,
    not functionality. All references to indent_level should be removed at some point.
"""
import sys
import os
from collections import namedtuple

DEBUG = os.getenv('DEBUG')

indent_level = 4
sample_data = {
    'title': 'The name of the thing',
    'author': 'A. A. Person',
    'other_book': [{'title': 'First Other Book',
                    'author': 'First Other Author'},
                   {'title': 'Second Other Book',
                    'author': 'Second Other Author',
                    'coauthor': [{'name': 'A. Co-Author',
                                  'age': 12.6,
                                  'word': ['many', 'many', 'words']
                                  },
                                 {'name': 'Another Co-Author',
                                  'word': ['in', 'other', 'words', 'maybe'],
                                  'number': 42000
                                  }
                                 ]
                    },
                   {'title': 'Third Other Book',
                    'author': 'Anonynmous'}
                   ]
}


def scalar2str(arg, title=''):
  """ Return a single li element with the value and possibly the title of the item.
      Handles strings, ints, and floats.
  """
  assert not (isinstance(arg, dict) or isinstance(arg, list) or isinstance(arg, tuple))
  if title == '':
    title_str = ''
  else:
    title_str = f'<strong>{title}:</strong> '

  if isinstance(arg, str):
    return f'{title_str}{arg}'
  if isinstance(arg, int):
    return f'{title_str}{arg:,}'
  if isinstance(arg, float):
    return f'{title_str}{arg:0.2f}'
  return 'unexpected'


def mk_dict(arg):
  try:
    return arg._asdict()
  except AttributeError as ae:
    return None


def items2html(arg, title='item'):
  """ If arg has multiple items, return a closeable list. Otherwise, return a single li.
  """
  global indent_level
  if DEBUG:
    print(f'*** items2html()', file=sys.stderr)
  assert isinstance(arg, list) or isinstance(arg, tuple)
  # If arg has an _asdict method, like a namedtuple, for example, pass the dict off to dict2html.
  d = mk_dict(arg)
  if d is not None:
    return dict2html(d, title)

  n = len(arg)
  suffix = 's' if n != 1 else ''
  html = f'\n{indent_level * "  "}<div>\n'
  indent_level += 1
  html += f'{indent_level * "  "}<h2 class="closer"><strong>' \
          f'{n} {title}{suffix}</strong></h2>\n{indent_level * "  "}<div><hr><ul>\n'
  indent_level += 1
  for i in range(len(arg)):
    item = arg[i]
    d = mk_dict(item)
    if d is not None:
      item = d
    if DEBUG:
      print(f'*** [{i}]; value: {item}', file=sys.stderr)
    if item is None:
      continue
    html += f'{indent_level * "  "}<li><strong>{title}[{i}]:</strong> '
    if isinstance(item, dict):
      indent_level += 1
      html += dict2html(item, 'item')
      indent_level -= 1
      html += f'{indent_level * "  "}</li>\n'
    elif isinstance(item, list) or isinstance(arg, tuple):
      indent_level += 1
      html += items2html(item, f'{title}[{i}]')
      indent_level -= 1
      html += f'{indent_level * "  "}</li>\n'
    else:
      html += scalar2str(item) + '</li>\n'
  indent_level -= 1
  html += f'{indent_level * "  "}</ul></div>\n'
  indent_level -= 1
  html += f'{indent_level * "  "}</div>\n'
  return html


def dict2html(arg, title=''):
  """ If arg has multiple items, return a closeable list. Otherwise, return a single li.
  """
  global indent_level
  if DEBUG:
    print(f'*** dict2html()', file=sys.stderr)
  assert isinstance(arg, dict)

  n = len(arg)
  suffix = 's' if n != 1 else ''
  html = f'\n{indent_level * "  "}<div>\n'
  indent_level += 1
  html += f'{indent_level * "  "}<h2 class="closer"><strong>{n} {title}{suffix}</strong>' \
          f'</h2>\n{indent_level * "  "}<div><hr><ul>\n'
  indent_level += 1
  for key, value in arg.items():
    if DEBUG:
      print(f'*** key: {key}; value: {value}', file=sys.stderr)
    if value is None:
      continue
    html += f'{indent_level * "  "}<li><strong>{key}: </strong> '
    if isinstance(value, dict):
      indent_level += 1
      html += dict2html(value)
      indent_level -= 1
      html += f'{indent_level * "  "}</li>\n'
    elif isinstance(value, list) or isinstance(value, tuple):
      indent_level += 1
      html += items2html(value, key)
      indent_level -= 1
      html += f'{indent_level * "  "}</li>\n'
    else:
      html += scalar2str(value) + '</li>\n'
  indent_level -= 1
  html += f'{indent_level * "  "}</ul></div>\n'
  indent_level -= 1
  return html + f'{indent_level * "  "}</div>\n'


if __name__ == '__main__':
  TestTuple = namedtuple('TestTuple', 'name age gender')
  tt = [TestTuple('No Name', 42, 'gen'),
        TestTuple('Some Name', 22, 'neg')]
  indent_level = 3
  print(f"""<!DOCTYPE html>
  <html lang="en">
    <head>
      <meta charset="utf-8"/>
      <title>Closeable Test</title>
      <script src="./closeable.js"></script>
      <link rel="stylesheet" href="./closeable.css">
    </head>
    <body>
<!--{items2html(tt, 'Book')}-->
{dict2html(sample_data, 'Book')}
    </body>
  </html>
""")
