/*  scrollable_tables.js
 *  Support for making table bodies scrollable with headers remaining stationary and header/body
 *  column widths remaining matched.
 */

//  content_width()
//  ---------------------------------------------------------------------------------------------
/*  Returns the content width of a table cell. Assuming border-collapse model, this means the
 *  computed width minus the sum of its left and right padding and the width of the wider of its
 *  left and right border.
 */
const content_width = (cell) =>
{
  let cell_style = getComputedStyle(cell);
  let pl = Number.parseInt(cell_style.getPropertyValue('padding-left'), 10);
  let pr = Number.parseInt(cell_style.getPropertyValue('padding-right'), 10);
  let bl = Number.parseInt(cell_style.getPropertyValue('border-left-width'), 10);
  let br = Number.parseInt(cell_style.getPropertyValue('border-right-width'), 10);
  let adj = pl + pr + Math.max(bl, br);
  return cell.getBoundingClientRect().width - adj;
};

//  set_height()
//  -----------------------------------------------------------------------------------------------
/*  Set the height of a ScrollableTable's parent div, presumably because the size of the viewable
 *  area changed.
 */
export const set_height = (scrollable_table) =>
{
  //  Get the parent element of the table and be sure is is a div of class table-height.
  const table_height_div = scrollable_table.parent_div;
  const table_top = table_height_div.offsetTop;
  const viewport_height = window.innerHeight;
  const fudge = 20; //  Room for bottom scrollbar and padding to be sure bottom of table shows
  let div_height = viewport_height - (table_top + fudge);
  // Check whether table will actually need to scroll or not.
  div_height = Math.min(div_height, scrollable_table.intrinsic_height);
  table_height_div.style.height = div_height + 'px';
  console.log(`set containing div height to ${div_height}px`);
};


// class ScrollableTable
// ================================================================================================
/* The first tbody element of a ScrollableTable will be scrollable, within the limits of the
 * desired_height, which can be changed via the set_height method.
 */
export default class ScrollableTable
{
  //  constructor()
  //  ---------------------------------------------------------------------------------------------
  /*  Makes a table element scrollable.
   */
  constructor(table, desired_height)
  {
    // Context
    // ............................................................................................
    this.table = table;
    this.desired_height = desired_height;
    this.thead = table.getElementsByTagName('thead')[0];
    let head_height = this.thead.offsetHeight;
    this.tbody = table.getElementsByTagName('tbody')[0];
    let body_height = this.tbody.offsetHeight;
    this.intrinsic_height = head_height + body_height;
    this.parent_div = this.table.parentNode; // Force this one's height to desired_height or less.

    // Attributes that make a table body scrollable
    // ............................................................................................
    this.thead.style.display = 'block';
    this.tbody.style.display = 'block';
    this.tbody.style.position = 'absolute';
    this.table.style.overflowY = 'hide';

    /* Adjust cell widths so that tbody cells line up with thead cells. If the table uses the
     * headers attribute to reference row and column positions, this is easy provided the column
     * ids end with '-col'. An alternative heuristic is used if this fails. */
    // ............................................................................................

    // Test if all cells in the first row of the body have proper headers attributes, including
    // at least one that ends with '-col'.
    // “Feature Request”: handle multiple -col headers (cases where multiple body cells match a
    // header cell with a rowspan > 1).
    let first_body_row_cells = this.tbody.children[0].children;
    let has_headers = true;
    let head_cells = [];
    let body_cells = [];
    for (let col = 0; col < first_body_row_cells.length; col++)
    {
      let body_cell = first_body_row_cells[col];
      if (body_cell.hasAttribute('headers'))
      {
        let headers_str = body_cell.getAttribute('headers');
        let col_id = null;
        let headers = headers_str.split(' ');
        for (let i = 0; i < headers.length; i++)
        {
          if (headers[i].match(/-col$/))
          {
            col_id = headers[i];
            break;
          }
        }
        if (col_id === null)
        {
          // console.log(`no -col in ${headers}`);
          has_headers = false;
          break;
        }
        let head_cell = document.getElementById(col_id);
        //  Save layout information for pairs of head/body cells in a column
        body_cells[col] = {cell: first_body_row_cells[col], width: content_width(body_cell)};
        head_cells[col] = {cell: head_cell, width: content_width(head_cell)};
      }
      else
      {
        // console.log('missing headers attribute(s)');
        has_headers = false;
        break;
      }
    }
    if (has_headers)
    {
      // Make the narrower of the header cell or body cell match the width of the wider of the two.
      for (let col = 0; col < head_cells.length; col++)
      {
        if (head_cells[col].cell.offsetWidth < body_cells[col].cell.offsetWidth)
        {
          head_cells[col].cell.style.minWidth = body_cells[col].width + 'px';
        }
        else
        {
          body_cells[col].cell.style.minWidth = head_cells[col].width + 'px';
        }
      }
    }
    else
    {
      // Alternative heuristic: find the row in thead with the largest number of cells, assume that
      // is the number of columns. If that matches the number of cells in the first row of the body,
      // do the width adjustment. If this fails, the table will be scrollable, but the columns
      // will not line up.
      let max_thead_cols_row_index = 0;
      let max_thead_cols_num_cols = 0;
      for (let row = 0; row < this.thead.children.length; row++)
      {
        let this_row = this.thead.children[row];
        if (this_row.children.length > max_thead_cols_num_cols)
        {
          max_thead_cols_row_index = row;
          max_thead_cols_num_cols = this_row.children.length;
        }
      }
      let head_cells = this.thead.children[max_thead_cols_row_index].children;
      let body_cells = this.tbody.children[0].children;
      if (head_cells.length === body_cells.length)
      {
        // Set the width of each cell in the row of thead with max cols to match the width of the
        // corresponding cols in the first row of tbody.
        for (let col = 0; col < head_cells.length; col++)
        {
          let head_cell = head_cells[col];
          let body_cell = body_cells[col];
          let head_cell_width = content_width(head_cell);
          let body_cell_width = content_width(body_cell);
          if (head_cell_width < body_cell_width)
          {
            head_cell.style.minWidth = body_cell_width + 'px';
          }
          else
          {
            body_cell.style.minWidth = head_cell_width + 'px';
          }
        }
      }
    }

    // Initialize the table's height
    set_height(this);
  }
}

// /*  Table elements with the class "scrollable" will have the thead column widths set to match the
//  *  widths of the columns of the tbody.
//  *
//  *  The table must have one thead section. The first tbody section will be scrollable.
//  *
//  *  The height of the table must be equal to the height of its containing element, such as a div
//  *  with no margin, border, or padding.
//  *
//  *  Tables to be scrollable must have the "scrollable" class, and their tbodys must have the
//  *  overflow-y property set to either "scroll" or "auto" depending on whether the scrollbars are
//  *  always to be visible, or visible only when the table needs to be scrolled.
//  */

// //  adjust_table()
// //  -----------------------------------------------------------------------------------------------
// /*  Make a table scrollable within a given height, which can be changed using set_height
//  */
// export function adjust_table(table)
// {
//   let thead = 'Undefined';
//   let tbody = 'Undefined';
//   const children = table.children;
//   for (let c = 0; c < children.length; c++)
//   {
//     let tag_name = children[c].tagName;
//     if (tag_name === 'THEAD')
//     {
//       if (thead === 'Undefined')
//       {
//         thead = children[c];
//       }
//       else
//       {
//         thead = 'Multple';
//       }
//     }
//     if (tag_name === 'TBODY')
//     {
//       if (tbody === 'Undefined')
//       {
//         tbody = children[c];
//       }
//       else
//       {
//         tbody = 'Multple';
//       }
//     }
//   }
//   //  If the table is scrollable, adjust the style properties and the width of the thead or tbody,
//   //  depending on which one is narrower.
//   if (thead !== 'Undefined' &&
//       thead !== 'Multiple' &&
//       tbody !== 'Undefined' &&
//       tbody !== 'Multiple')
//   {
//     // Set the height of the tbody. Do this by getting the height of the table minus the height of
//     // the thead. The height of the table is the height of its containing element; the table
//     // itself does not give an accurate measure.
//     const table_height = table.parentNode.offsetHeight;
//     table.style.overflowY = 'hide';
//     const head_height = thead.offsetHeight;
//     tbody.style.height = (table_height - head_height) + 'px';
//     thead.style.display = 'block';
//     tbody.style.display = 'block';
//     tbody.style.position = 'absolute';

//     //  See if all the cells in the first body row have the headers attribute, and that each one
//     //  contains a header that ends with '-col'.
//     //  If so, the xxx-col header is the id of the cell in the thead whose width is to be matched.
//     //  NOTE: headers/id attributes are an accessibility feature that allows table cells to be
//     //  associated unambiguously with row and column headers. This algorithm adopts the convention
//     //  that there must be exactly one thead cell that will be used for setting each column's
//     //  width, and that its id ends with '-col'.
//     const body_row = tbody.children[0].children;
//     let has_headers = true;
//     let head_cells = [];
//     let body_cells = [];
//     for (let i =0; i < body_row.length; i++)
//     {
//       if (body_row[i].hasAttribute('headers'))
//       {
//         let headers_str = body_row[i].getAttribute('headers');
//         let col_id = null;
//         let headers = headers_str.split(' ');
//         for (let i = 0; i < headers.length; i++)
//         {
//           if (headers[i].match(/-col$/))
//           {
//             col_id = headers[i];
//             break;
//           }
//         }
//         if (col_id === null)
//         {
//           console.log(`no -col in ${headers}`);
//           has_headers = false;
//           break;
//         }
//         let body_cell_style = getComputedStyle(body_row[i]);
//         let pl = Number.parseInt(body_cell_style.getPropertyValue('padding-left'), 10);
//         let pr = Number.parseInt(body_cell_style.getPropertyValue('padding-right'), 10);
//         let bl = Number.parseInt(body_cell_style.getPropertyValue('border-left-width'), 10);
//         let br = Number.parseInt(body_cell_style.getPropertyValue('border-right-width'), 10);
//         let adj = pl + pr + Math.max(bl, br);
//         body_cells[i] = {cell: body_row[i],
//           width: body_row[i].getBoundingClientRect().width - adj};
//         let head_cell = document.getElementById(col_id);
//         let head_cell_style = getComputedStyle(head_cell);
//         pl = Number.parseInt(head_cell_style.getPropertyValue('padding-left'), 10);
//         pr = Number.parseInt(head_cell_style.getPropertyValue('padding-right'), 10);
//         bl = Number.parseInt(head_cell_style.getPropertyValue('border-left-width'), 10);
//         br = Number.parseInt(head_cell_style.getPropertyValue('border-right-width'), 10);
//         adj = pl + pr + Math.max(bl, br);
//         head_cells[i] = {cell: head_cell,
//           width: head_cell.getBoundingClientRect().width - adj};
//       }
//       else
//       {
//         // console.log('missing headers attribute(s)');
//         has_headers = false;
//         break;
//       }
//     }
//     if (has_headers)
//     {
//       for (let col = 0; col < head_cells.length; col++)
//       {
//         if (head_cells[col].cell.offsetWidth < body_cells[col].cell.offsetWidth)
//         {
//           head_cells[col].cell.style.minWidth = body_cells[col].width + 'px';
//         }
//         else
//         {
//           body_cells[col].cell.style.minWidth = head_cells[col].width + 'px';
//         }
//       }
//     }
//     else
//     {
//       // Table does not have id/headers attributes, so fall back to number of columns heuristic
//       // Find the thead row with the max number of columns
//       let max_thead_cols_row_index = 0;
//       let max_thead_cols_num_cols = 0;
//       for (let row = 0; row < thead.children.length; row++)
//       {
//         let this_row = thead.children[row];
//         if (this_row.children.length > max_thead_cols_num_cols)
//         {
//           max_thead_cols_row_index = row;
//           max_thead_cols_num_cols = this_row.children.length;
//         }
//       }
//       const head_row = thead.children[max_thead_cols_row_index].children;

//       if (thead.offsetWidth < tbody.offsetWidth)
//       {
//         // Set the width of each cell in the row of thead with max cols to match the width of the
//         // corresponding cols in the first row of tbody.
//         for (let head_col = 0; head_col < head_row.length; head_col++)
//         {
//           let cell_style = getComputedStyle(head_row[head_col]);
//           let l_padding = cell_style.getPropertyValue('padding-left').match(/\d+/)[0] - 0;
//           let r_padding = cell_style.getPropertyValue('padding-right').match(/\d+/)[0] - 0;
//           let h_padding = l_padding + r_padding;
//           head_row[head_col].style.minWidth = (body_row[head_col].clientWidth - h_padding) + 'px';
//         }
//       }
//       else
//       {
//         // Set the width of each cell in the first body row to match the width of the corresponding
//         // cells in the header row with max number of columns.
//         for (let body_col = 0; body_col < body_row.length; body_col++)
//         {
//           let cell_style = getComputedStyle(body_row[body_col]);
//           let l_padding = cell_style.getPropertyValue('padding-left').match(/\d+/)[0] - 0;
//           let r_padding = cell_style.getPropertyValue('padding-right').match(/\d+/)[0] - 0;
//           let h_padding = l_padding + r_padding;
//           body_row[body_col].style.minWidth = (head_row[body_col].clientWidth - h_padding) + 'px';
//         }
//       }
//     }
//   }
// }
// // // HACK: For certain header configurations (namely. when the row with the largest number of
// // // columns is not the widest thead row), the initial adjustment is wrong, but running the
// // // functions again (for example by resizing the viewport) fixes it.
// // if (event.type !== 'dummy')
// // {
// //   adjust_tables({type: 'dummy'});
// // }


// //  set_height()
// //  -----------------------------------------------------------------------------------------------
// /*  Set the height of a table's parent div, presumably because the size of the viewable area
//  *  changed.
//  */
// export const set_height = (table) =>
// {
//   //  Get the parent element of the table and be sure is is a div of class table-height.
//   let table_height_div = table.parent;
//   console.log(table_height_div);
//   //  Make the (only) table of the current document fill the current viewport, and no more.
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
//       //  This is the first reference to the table: save its initial height.
//       const thead = table_height_div.getElementsByTagName('thead')[0];
//       const tbody = table_height_div.getElementsByTagName('tbody')[0];
//       let table_height = thead.clientHeight + tbody.clientHeight;
//       table.setAttribute('scrollable-table-height', `${table_height}`);
//       div_height = Math.min(div_height, table_height);
//     }
//     table_height_div.style.height = div_height + 'px';
//   }
// };
