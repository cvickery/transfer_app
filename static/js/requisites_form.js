
//  check_status()
//  -----------------------------------------------------------------------------------------------
/*  Disable the submit button unless all controls have non-empty values.
 */
const check_status = function()
{
  if (document.getElementById('institution').value === '' ||
      document.getElementById('block-type').value === '' ||
      document.getElementById('block-value').value === '')
  {
    document.getElementById('goforit').disabled = true;
  }
  else
  {
    document.getElementById('goforit').disabled = false;
  }

};

//  values_listener()
//  -----------------------------------------------------------------------------------------------
/*  AJAX listener for block_value options.
 */
const values_listener = function()
{
  document.getElementById('block-value').innerHTML = this.response;
  document.getElementById('value-div').style.display = 'block';
  check_status();
};

//  update_values()
//  -----------------------------------------------------------------------------------------------
/*  Initiate AJAX request for block_value options.
 */
const update_values = function()
{
  const institution = document.getElementById('institution').value;
  const block_type = document.getElementById('block-type').value;
  if (institution !== '' && block_type !== '')
  {
    const request = new XMLHttpRequest();
    request.addEventListener('load', values_listener);
    request.open('GET',
      `/_requisite_values/?institution=${institution}&block_type=${block_type}`);
    request.send();
  }
  // Hide block-value and disable submit button until choices return
  document.getElementById('value-div').style.display = 'none';
};

//  main()
//  -----------------------------------------------------------------------------------------------
/*  Set up listeners
 */
const main = function()
{
  document.getElementById('institution').addEventListener('change', update_values);
  document.getElementById('block-type').addEventListener('change', update_values);
  document.getElementById('block-value').addEventListener('change', check_status);

  // Initial UI state
  document.getElementById('value-div').style.display = 'none';
  document.getElementById('goforit').disabled = true;
};

window.addEventListener('load', main);

