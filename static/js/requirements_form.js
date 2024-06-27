
// value_change()
// ------------------------------------------------------------------------------------------------
/* Submit the form when the block-value changes.
 */
const value_change = function()
{
  document.getElementById('requirement-id').value = document.getElementById('block-value').value;
  if (document.getElementById('block-select-form').requestSubmit)
  {
    document.getElementById('block-select-form').requestSubmit();
  }
  else
  {
    document.getElementById('block-select-form').submit();
  }
}

//  values_listener()
//  -----------------------------------------------------------------------------------------------
/*  AJAX listener for block_value options.
 */
const values_listener = function ()
{
  document.getElementById('block-value-div').innerHTML = this.response;
  document.getElementById('block-value-label').style.color = '#000000';
  document.getElementById('block-value').addEventListener('change', value_change);
};

//  update_values()
//  -----------------------------------------------------------------------------------------------
/*  Initiate AJAX request for block_value options.
 */
const update_values = function ()
{
  const institution = document.querySelector('input[name="institution"]:checked').value;
  const block_type = document.getElementById('block-type').value;
  if (institution !== '' && block_type !== '')
  {
    const bv_label = document.getElementById('block-value-label');
    if (bv_label)
    {
      bv_label.style.color = '#ff0099';
    }
    const request = new XMLHttpRequest();
    request.addEventListener('load', values_listener);
    request.open('GET',
      `/_requirement_values/?institution=${institution}&block-type=${block_type}`);
    request.send();
  }
};

// requirement_num_change()
// ------------------------------------------------------------------------------------------------
/* Convert num to requirement_id, set it, and submit form.
 */
const requirement_num_change = function()
{
  try
  {
    let requirement_num = document.getElementById('requirement-num').value.match(/\d{1,6}/)[0];
    while (requirement_num.length < 6)
    {
      requirement_num = '0' + requirement_num;
    }
    const requirement_id = 'RA' + requirement_num;
    document.getElementById('requirement-id').value = requirement_id;
    document.getElementById('select-block-form').requestSubmit();
  }
  catch (error)
  {
    console.log(`Line 83: ${error}`);
  }

}

// block_type_change()
// ------------------------------------------------------------------------------------------------
/* Populate and display block-value-div
 */
const block_type_change = function()
{
  update_values();
}

//  college_change()
//  -----------------------------------------------------------------------------------------------
/* Display id-or-type-div, but not value-div
 */
const college_change = function()
{
  document.getElementById('id-or-type-div').style.display = 'block';
  document.getElementById('requirement-num').value = '';
  update_values();
}

//  main()
//  -----------------------------------------------------------------------------------------------
/*  Set up listeners and initialize display
 *    The institution-option div is always shown.
 *    The id-or-type div is shown whenever an institution has been selected, but not otherwise.
 */
const main = function ()
{
  document.getElementById('block-type').addEventListener('change', block_type_change);
  var college_radios = document.querySelectorAll('[type=radio]');
  var college_selected = [...college_radios].some(radio => radio.checked);
  [...college_radios].forEach(radio => radio.addEventListener('change', college_change));

  document.getElementById('requirement-num').addEventListener('change', requirement_num_change);

  // Initial UI state: depends on whether an institution is selected or not.
  if (college_selected) {
    document.getElementById('id-or-type-div').style.display = 'block';
    college_change();
  }
  else {
    document.getElementById('id-or-type-div').style.display = 'none';
  }
};

window.addEventListener('load', main);

