#! /usr/local/bin/python3
"""Application-wide common header generator."""


def header(title, nav_items=[]):
    """Return an html header element containing logo, title, and a list of nav items."""
    nav_element = "<nav>"
    nav_elements = []
    for nav_item in nav_items:
        if nav_item["type"] == "button":
            # Nav buttons can have either a class or a id for js event handling.
            try:
                class_attribute = f'class="{nav_item["class"]}" '
            except KeyError:
                class_attribute = ""
            try:
                id_attribute = f'id="{nav_item["id"]}" '
            except KeyError:
                id_attribute = ""
            button_attributes = (id_attribute + class_attribute).strip()
            assert button_attributes != "", "Missing id or class for nav button"
            nav_elements.insert(
                0,
                f"<button {button_attributes} "
                f'        class="nav-button">{nav_item["text"]}</button>',
            )
        else:
            nav_elements.insert(
                0, f'<a href="{nav_item["href"]}"   class="nav-link">{nav_item["text"]}</a>'
            )
    nav_element += f"{''.join(nav_elements)}</nav>"

    return f"""<header>
               <a href="https://trexlabs.org">
                 <img src="/static/images/labs_logo.png" alt="Labs Logo">
               </a>
               <span class="header-title">{title}</span>
               {nav_element}
              </header>
          """


if __name__ == "__main__":
    print(
        header(
            title="Testing Title",
            nav_items=[
                {"text": "Main Menu", "type": "button", "id": "main-menu"},
                {"type": "link", "href": "/", "text": "Change Settings"},
            ],
        )
    )
