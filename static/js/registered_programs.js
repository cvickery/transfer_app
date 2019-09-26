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

// //  set_height()
// //  -----------------------------------------------------------------------------------------------
// /*  Set the height of all table-height divs in preparation for adjusting the scrollable tables
//  *  contained therein.
//  *  Calls adjust_tables() after (re-)setting heights.
//  */
// const set_height = () =>
// {
//   //  Make the (only) table on this page fill the current viewport, and no more.
//   //  Is there a table?
//   const table_height_divs = document.getElementsByClassName('table-height');
//   if (table_height_divs.length > 0)
//   {
//     const table_height_div = table_height_divs[0];
//     const table_top = table_height_div.offsetTop;
//     const viewport_height = window.innerHeight;
//     const fudge = 20; //  Room for bottom scrollbar and padding to be sure bottom of table shows
//     let div_height = viewport_height - (table_top + fudge);
//     // Check whether table will actually need to scroll or not.
//     const table = table_height_div.getElementsByTagName('table')[0];
//     if (table.hasAttribute('scrollable-table-height'))
//     {
//       div_height = Math.min(div_height,
//         Number.parseInt(table.getAttribute('scrollable-table-height'), 10));
//     }
//     else
//     {
//       const thead = table_height_div.getElementsByTagName('thead')[0];
//       const tbody = table_height_div.getElementsByTagName('tbody')[0];
//       let table_height = thead.clientHeight + tbody.clientHeight;
//       table.setAttribute('scrollable-table-height', `${table_height}`);
//       div_height = Math.min(div_height, table_height);
//     }
//     table_height_div.style.height = div_height + 'px';
//   }
// };

//  Page Load Event Listener
//  -----------------------------------------------------------------------------------------------
/*  Make initial call to set_height() and set up  set_heights listeners for window resize and
 *  details toggle events.
 */
window.addEventListener('load', function ()
{
  // Adjust tables on initial page load.
  set_height();
  adjust_tables();
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
