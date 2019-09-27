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
  return Math.round(cell.getBoundingClientRect().width - adj);
};



// class ScrollableTable
// ================================================================================================
/* The first tbody element of a ScrollableTable will be scrollable, within the limits of the
 * desired_height, which can be changed via the adjust_height method.
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
    this.parent_node = this.table.parentNode; // Force this one's height to desired_height or less.

    // Attributes that make a table body scrollable
    // ............................................................................................
    this.thead.style.display = 'block';
    this.tbody.style.display = 'block';
    this.parent_node.style.position = 'relative';
    this.tbody.style.position = 'absolute';
    this.table.style.overflowY = 'hidden';
    console.log('before width adjustments', this);

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
        console.log('alternative heuristic');
        // Set the width of each cell in the row of thead with max cols to match the width of the
        // corresponding cols in the first row of tbody.
        for (let col = 0; col < head_cells.length; col++)
        {
          let head_cell = head_cells[col];
          let body_cell = body_cells[col];
          let head_cell_width = content_width(head_cell);
          let body_cell_width = content_width(body_cell);
          console.log('before', head_cell_width, body_cell_width);
          if (head_cell_width < body_cell_width)
          {
            head_cell.style.minWidth = body_cell_width + 'px';
          }
          else
          {
            body_cell.style.minWidth = head_cell_width + 'px';
          }
          console.log('after', content_width(head_cell), content_width(body_cell));
        }
      }
      else
      {
        console.error(`table is not scrollable: ${head_cells.length}; !== ${body_cells.length} `);
      }
    }

    // Initialize the table's height
    if (this.desired_height)
    {
      // The height is a known value
      this.parent_node.style.height = this.desired_height + 'px';
    }
    else
    {
      //  Height is based on space remaining in the viewport
      console.log('before adjust_height ', this);
      this.adjust_height();
    }
  }

  //  adjust_height()
  //  -----------------------------------------------------------------------------------------------
  /*  Change the height of a ScrollableTable's parent div, presumably because the size of the
   *  viewable area changed.
   */
  adjust_height()
  {
    console.log('adjust_height()', this);
    //  Get the parent element of the table and be sure is is a div of class table-height.
    const table_height_div = this.parent_node;
    const table_top = table_height_div.offsetTop;
    const viewport_height = window.innerHeight;
    const fudge = 20; //  Room for bottom scrollbar and padding to be sure bottom of table shows
    let div_height = viewport_height - (table_top + fudge);
    // Check whether table will actually need to scroll or not.
    div_height = Math.min(div_height, this.intrinsic_height);
    table_height_div.style.height = div_height + 'px';
    console.log(`set containing div height to ${div_height}px`, this);
  }

}
