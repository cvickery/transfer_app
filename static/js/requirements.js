/*  A "closeable" is an element for which the contents (first child) can be opened or closed.
 */


window.addEventListener('load', function()
{
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
});
