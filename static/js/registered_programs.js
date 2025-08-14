// import ScrollableTable from './scrollable_tables.js';

//  Page Load Event Listener
//  -----------------------------------------------------------------------------------------------
window.addEventListener('load', function ()
{
  // Submit the associated form automatically when any <select> changes
  document.querySelectorAll('select').forEach(function (select)
  {
    select.addEventListener('change', function ()
    {
      select.closest('form').submit();
    });
  });

  // 2025-08-13
  // Now that CSS implements the "sticky" value for position of <thead> elements, all that follows
  // is no longer needed, and the whole ScrollableTables project is no longer needed of any use.
  
  /* 
  	// Make all the tables (if there are any) scrollable: for this app, there is just the one for
  	// the selected college (or all colleges) ... or none.
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
                                            desired_height: `${height_value} ${height_unit}`});
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
  */
});
