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
/*  Make the table of programs scrollable, and responsive to windo resize and details toggle events.
 */
window.addEventListener('load', function ()
{
  // Make the table (if there is one) scrollable.
  const tables = document.getElementsByClassName('scrollable');
  if (tables.length > 0)
  {
    const the_table = new ScrollableTable({table: tables[0], padding: 12});
    const adjust_table = the_table.get_adjustment_callback();

    // Need to re-process the table's height when viewport is resized.
    window.addEventListener('resize', adjust_table);
    // Need to re-process table when details elements open/close.
    const details = document.getElementsByTagName('details');
    if (details)
    {
      for (let i = 0; i < details.length; i++)
      {
        details[i].addEventListener('toggle', adjust_table);
      }
    }
  }
});
