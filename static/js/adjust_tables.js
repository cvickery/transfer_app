/*  Table elements with the class "scrollable" will have the thead column widths set to match the
 *  widths of the columns of the tbody.
 *
 *  TODO: Adjust for different cell border widths between the thead and tbody
 *
 *  The table must have one thead section. The first tbody section will be scrollable.
 *
 *  The height of the table must be equal to the height of its containing element, such as a div
 *  with no margin, border, or padding.
 *
 *  Tables to be scrollable must have the "scrollable" class, and their tbodys must have the
 *  overflow-y property set to either "scroll" or "auto" depending on whether the scrollbars are
 *  always to be visible, or visible only when the table needs to be scrolled.
 */

//  adjust_tables()
//  -----------------------------------------------------------------------------------------------
/*  Find all scrollable tables and make their bodies scrollable, as it were.
 */
export default function adjust_tables(event)
{
  // console.log(`adjust_tables(${event.type})`);
  //  Find all tables with the scrollable class and containing exactly one thead and one tbody.
  const scrollable_elements = document.getElementsByClassName('scrollable');
  let scrollable_tables = [];
  for (let i = 0; i < scrollable_elements.length; i++)
  {
    if (scrollable_elements[i].tagName === 'TABLE')
    {
      scrollable_tables.push(scrollable_elements[i]);
    }
  }

  for (let i = 0; i < scrollable_tables.length; i++)
  {
    // A table must have one thead and one tbody to be scrollable.
    let table = scrollable_tables[i];
    let thead = 'Undefined';
    let tbody = 'Undefined';
    const children = table.children;
    for (let c = 0; c < children.length; c++)
    {
      let tag_name = children[c].tagName;
      if (tag_name === 'THEAD')
      {
        if (thead === 'Undefined')
        {
          thead = children[c];
        }
        else
        {
          thead = 'Multple';
        }
      }
      if (tag_name === 'TBODY')
      {
        if (tbody === 'Undefined')
        {
          tbody = children[c];
        }
        else
        {
          tbody = 'Multple';
        }
      }
    }
    //  If the table is scrollable, adjust the style properties and the width of the thead or tbody,
    //  depending on which one is narrower.
    if (thead !== 'Undefined' &&
        thead !== 'Multiple' &&
        tbody !== 'Undefined' &&
        tbody !== 'Multiple')
    {
      // Set the height of the tbody. Do this by getting the height of the table minus the height of
      // the thead. The height of the table is the height of its containing element; the table
      // itself does not give an accurate measure.
      const table_height = table.parentNode.offsetHeight;
      table.style.overflowY = 'hide';
      const head_height = thead.offsetHeight;
      tbody.style.height = (table_height - head_height) + 'px';
      thead.style.display = 'block';
      tbody.style.display = 'block';
      tbody.style.position = 'absolute';

      //  See if all the cells in the body row have the headers attribute
      const body_row = tbody.children[0].children;
      let has_headers = true;
      let col_widths = {};
      for (let i =0; i < body_row.length; i++)
      {
        if (body_row[i].hasAttribute('headers'))
        {
          let col_id = body_row[i].getAttribute('headers');
          col_widths[col_id] = body_row[i].clientWidth;
        }
        else
        {
          has_headers = false;
          break;
        }
      }
      if (has_headers)
      {
        // I think you still have to test whether the thead or the tbody is wider here.
        // Or maybe you just see which is wider cell-by-cell above and use the larger for whichever
        // is smaller.
        // Or maybe you go to bed now.
      }
      // Find the thead row with the max number of columns
      let max_thead_cols_row_index = 0;
      let max_thead_cols_num_cols = 0;
      for (let row = 0; row < thead.children.length; row++)
      {
        let this_row = thead.children[row];
        if (this_row.children.length > max_thead_cols_num_cols)
        {
          max_thead_cols_row_index = row;
          max_thead_cols_num_cols = this_row.children.length;
        }
      }
      const head_row = thead.children[max_thead_cols_row_index].children;

      if (thead.offsetWidth < tbody.offsetWidth)
      {
        // Set the width of each cell in the row of thead with max cols to match the width of the
        // corresponding cols in the first row of tbody.
        for (let head_col = 0; head_col < head_row.length; head_col++)
        {
          let cell_style = getComputedStyle(head_row[head_col]);
          let l_padding = cell_style.getPropertyValue('padding-left').match(/\d+/)[0] - 0;
          let r_padding = cell_style.getPropertyValue('padding-right').match(/\d+/)[0] - 0;
          let h_padding = l_padding + r_padding;
          head_row[head_col].style.minWidth = (body_row[head_col].clientWidth - h_padding) + 'px';
        }
      }
      else
      {
        // Set the width of each cell in the first body row to match the width of the corresponding
        // cells in the header row with max number of columns.
        for (let body_col = 0; body_col < body_row.length; body_col++)
        {
          let cell_style = getComputedStyle(body_row[body_col]);
          let l_padding = cell_style.getPropertyValue('padding-left').match(/\d+/)[0] - 0;
          let r_padding = cell_style.getPropertyValue('padding-right').match(/\d+/)[0] - 0;
          let h_padding = l_padding + r_padding;
          body_row[body_col].style.minWidth = (head_row[body_col].clientWidth - h_padding) + 'px';
        }
      }
    }
  }
  // HACK: For certain header configurations (namely. when the row with the largest number of
  // columns is not the widest thead row), the initial adjustment is wrong, but running the
  // functions again (for example by resizing the viewport) fixes it.
  if (event.type !== 'dummy')
  {
    adjust_tables({type: 'dummy'});
  }
}
