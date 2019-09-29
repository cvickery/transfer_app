import ScrollableTable from './scrollable_tables.js';

$(function()
{
  //  Submit button not needed if JS is running ’cause this code does it automatically.
  //  But people want to see it, so just ignore it.
  $('select').change(function()
  {
    $('form').submit();
  });
});

//  Page Load Event Listener
//  -----------------------------------------------------------------------------------------------
/*  Make initial call to set_height() and set up  set_heights listeners for window resize and
 *  details toggle events.
 */
window.addEventListener('load', function ()
{
  // Make the table (if there is one) scrollable.
  const tables = document.getElementsByClassName('scrollable');
  if (tables.length > 0)
  {
    const the_table = new ScrollableTable(tables[0]);
    const get_height = the_table.get_height_callback();

    // Need to re-process the table's height when viewport is resized.
    window.addEventListener('resize', get_height);
    // Need to re-process table when details elements open/close.
    const details = document.getElementsByTagName('details');
    if (details)
    {
      for (let i = 0; i < details.length; i++)
      {
        details[i].addEventListener('toggle', get_height);
      }
    }
  }
});
