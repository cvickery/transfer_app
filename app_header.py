#! /usr/local/bin/python3
"""
"""


def header(title, nav_items=[]):
  """ Return an html header element containing logo, title, and a list of nav items.
  """
  nav_element = '<nav>'
  nav_elements = []
  for nav_item in nav_items:
    if nav_item['type'] == 'button':
      nav_elements.insert(0, f"<button id=\"{nav_item['id']}\" "
                             f"        class=\"nav-button\">{nav_item['text']}</button>")
    else:
      nav_elements.insert(0, f"<a href=\"{nav_item['href']}\""
                             f"   class=\"nav-link\">{nav_item['text']}</a>")
  nav_element += f'{"".join(nav_elements)}</nav>'

  return(f"""<header>
               <a href="https://cuny.edu">
                 <img src="/static/images/cuny_logo.png" alt="CUNY Logo">
               </a>
               <span class="header-title">{title}</span>
               {nav_element}
             </header>
          """)


if __name__ == '__main__':
  print(header(title='Testing Title',
               nav_items=[{'text': 'Main Menu', 'type': 'button', 'id': 'main-menu'},
                          {'type': 'link', 'href': '/', 'text': 'Change Settings'}]))
