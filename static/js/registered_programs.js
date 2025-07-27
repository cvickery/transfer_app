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
  for (const table_element of tables)
  {
    let height_value = 100;
    let height_unit = 'vu';
    const height_attribute = table_element.getAttribute('height').trim();
    if (height_attribute)
    {
      // Allowed units are px and vh: treat % as vh
      const match = height_attribute.match(/^([\d.]+)(px|%|vh)$/i);
      if (match)
      {
        height_value = parseFloat(match[1]);
        height_unit = match[2].toLowerCase() === '%' ? 'vh' : match[2].toLowerCase();;

      }
      else
      {
        console.warn(`Invalid scrollable table height: "${height}"`);
      }
    }
    console.log(`Scrollable table height: ${height_value} ${height_unit}`);

    const the_table = new ScrollableTable({table: table_element, use_heading: true,
                                           height_value: height_value, height_unit: height_unit});
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
