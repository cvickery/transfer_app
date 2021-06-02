/*  A "closeable" is an element for which the contents (first child) can be opened or closed.
 */

window.addEventListener('load', function()
{
  return;
  // Typing ESC while hovering over a closer toggles between open and closed.
  const details = document.getElementsByTagName('details');
  for (let i = 0; i < details.length; i++)
  {
    // This is only getting keyup events when the focus is on the summary, not the body of the
    // details elements, which defeats the purpose of wanting to close (toggle) the state by
    // typing escape while hovering over the body part. Sigh.
    // But it works for dblclick
    details[i].addEventListener('dblclick', function(e)
    {
      let target = e.target;
      while (target.tagName !== 'DETAILS')
      {
        target = target.parentElement;
      }
      target.toggleAttribute('open');
    });
  }


  const closers = document.getElementsByClassName('closer');
  for (let i = 0; i < closers.length; i++)
  {
    // Add the closeable class to the first child
    closers[i].classList.add('open');
    closers[i].nextElementSibling.classList.add('closeable');
    closers[i].addEventListener('click', function()
    {
      // Toggle the closer's triangle and the closee's display
      this.classList.toggle('open');
      if (this.classList.contains('open'))
      {
        this.nextElementSibling.style.display = 'block';
      }
      else
      {
        this.nextElementSibling.style.display = 'none';
      }
    });
  }

  // //  Clicking in a Scribe Block's text toggles line numbers
  // const code_sections = document.getElementsByClassName('with-numbers');
  // for (let i = 0; i < code_sections.length; i++)
  // {
  //   code_sections[i].addEventListener('click', function()
  //   {
  //     const pre_element = this.getElementsByClassName('line-numbers')[0];
  //     pre_element.classList.toggle('open');
  //     if (pre_element.classList.contains('open'))
  //     {
  //       pre_element.style.display = 'block';
  //     }
  //     else
  //     {
  //       pre_element.style.display = 'none';
  //     }
  //   });
  // }

});
