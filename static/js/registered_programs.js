import adjust_tables from './adjust_tables.js';

$(function()
{
  //  Submit button not needed if JS is running ’cause this code does it automatically.
  //  But people want to see it, so just ignore it.
  $('select').change(function()
  {
    $('form').submit();
  });
});

const set_height = () =>
{
  //  Make the (only) table on this page fill the current viewport, and no more.
  //  Is there a table?
  const table_height_divs = document.getElementsByClassName('table-height');
  if (table_height_divs.length > 0)
  {
    const table_height_div = table_height_divs[0];
    const table_top = table_height_div.offsetTop;
    const viewport_height = window.innerHeight;
    table_height_div.style.height = (viewport_height - table_top) + 'px';
    adjust_tables({type: 'set-height'});
  }
};

window.addEventListener('load', function (event)
{
  set_height(event);
  // Need to re-process tables when viewport is resized.
  window.addEventListener('resize', set_height);
  // Need to re-process tables when details open/close.
  const details = document.getElementsByTagName('details');
  if (details)
  {
    for (let i = 0; i < details.length; i++)
    {
      details[i].addEventListener('toggle', set_height);
    }
  }
});

// Wait for the document to load or resize, and adjust all scrollable tables on the page.
// window.addEventListener('load', adjust_tables);
// window.addEventListener('resize', adjust_tables);
