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
  let pl = Number.parseFloat(cell_style.getPropertyValue('padding-left'), 10);
  let pr = Number.parseFloat(cell_style.getPropertyValue('padding-right'), 10);
  let bl = Number.parseFloat(cell_style.getPropertyValue('border-left-width'), 10);
  let br = Number.parseFloat(cell_style.getPropertyValue('border-right-width'), 10);
  let adj = pl + pr + Math.max(bl, br);
  return cell.getBoundingClientRect().width - adj;
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
  /*  Makes a table body scrollable while column headers stay in position.
   *  The height of the table can be given explicitly or can be determined from the space remaining
   *  in the viewport.
   */
  constructor(args)
  {
    // Context
    // ............................................................................................
    this.table = args.table;
    this.desired_height = args.height;
    this.initial_delay = args.delay ? args.delay : 2000;
    this.padding_bottom = args.padding ? args.padding : 10;
    this.use_headeing_widths = args.use_headeing_widths;

    this.thead = this.table.getElementsByTagName('thead')[0];
    let head_height = this.thead.offsetHeight;
    this.tbody = this.table.getElementsByTagName('tbody')[0];
    let body_height = this.tbody.offsetHeight;
    this.intrinsic_height = head_height + body_height;
    this.parent_node = this.table.parentNode; // Force this one's height to desired_height or less.

    // Attributes that make a table body scrollable
    // ............................................................................................
    this.thead.style.display = 'block';
    this.tbody.style.display = 'block';
    this.tbody.style.position = 'absolute';

    // initial adjustments
    this.adjust_height();
    this.adjust_widths();
    setTimeout(function ()
    {
      // Cleanup Heuristic.
      // Wait for table layout to complete, and then readjust the table again.
      // If the table is too long for layout to complete layout within the default delay interval,
      // the code that creates this object should specify a longer initial_delay.
      this.adjust_table();
    }.bind(this), this.initial_delay);
  }


  // adjust_table()
  // ----------------------------------------------------------------------------------------------
  /* Adjust the table’s height and width.
   */
  adjust_table()
  {
    this.adjust_height();
    this.adjust_widths();
  }

  // get_adjustment_callback()
  // ----------------------------------------------------------------------------------------------
  /* Provide a reference to this object’s adjust_height method, bound to ‘this’. I don’t understand
   * why the object returned by the constructor doesn’t take care of this, but I think it’s because
   * ES6 classes are just syntactic sugar for nested functions, so the closure has to be handled
   * explicitly.
   *
   * Used for setting up event listeners when window is resized or details elements toggle state.
   */
  get_adjustment_callback()
  {
    return this.adjust_table.bind(this);
  }


  //  adjust_height()
  //  ---------------------------------------------------------------------------------------------
  /*  Change the height of a ScrollableTable's parent div: initially, or because of an event that
   *  makes it necessary to do so.
   */
  adjust_height()
  {
    const table_top = this.parent_node.offsetTop;
    const viewport_height = window.innerHeight;
    let div_height = viewport_height - (table_top + this.padding_bottom);
    if (this.desired_height)
    {
      // The height is a known value
      div_height = Math.min(div_height, this.desired_height);
    }
    else
    {
      // The height depends on the space available.
      div_height = Math.min(div_height, this.intrinsic_height);
    }

    //  Adjust the height of the parent node, and make the body fit.
    this.parent_node.style.height = (div_height + this.padding_bottom) + 'px';
    this.tbody.style.height = (div_height - this.thead.offsetHeight) + 'px';
  }


  // adjust_widths()
  // ----------------------------------------------------------------------------------------------
  /* Adjust cell widths so that tbody cells line up with thead cells. If the table uses the
   * headers attribute to reference row and column positions, this is easy, provided the column
   * ids end with '-col'. Uses an alternative heuristic if that requirement does not obtain. */
  adjust_widths()
  {
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
        has_headers = false;
        break;
      }
    }
    if (has_headers)
    {
      // Make the narrower of the header cell or body cell match the width of the wider of the two.
      for (let col = 0; col < head_cells.length; col++)
      {
        if (this.user_header_widths ||
            head_cells[col].cell.offsetWidth > body_cells[col].cell.offsetWidth)
        {
          body_cells[col].cell.style.minWidth = head_cells[col].width + 'px';
        }
        else
        {
          head_cells[col].cell.style.minWidth = body_cells[col].width + 'px';
        }
      }
    }
    else
    {
      // Alternate heuristic: find the row in thead with the largest number of cells, assume that
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
          if (this.user_header_widths ||
              head_cell_width > body_cell_width)
          {
            body_cell.style.minWidth = head_cell_width + 'px';
          }
          else
          {
            head_cell.style.minWidth = body_cell_width + 'px';
          }
        }
      }
      else
      {
        console.error(`Unable to adjust widths: ${head_cells.length} !== ${body_cells.length}`);
      }
    }
  }
}
