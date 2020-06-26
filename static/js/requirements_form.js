
let was_selected = '';
//  check_status()
//  -----------------------------------------------------------------------------------------------
/*  Disable the submit button unless all controls have non-empty values.
 */
const check_status = function ()
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
const values_listener = function ()
{
  document.getElementById('block-value').innerHTML = this.response;
  const options = document.getElementById('block-value').options;
  for (let i = 0; i < options.length; i++)
  {
    if (options.item(i).value === was_selected)
    {
      options.item(i).selected = true;
      break;
    }
  }
  document.getElementById('value-div').style.display = 'block';
  check_status();
};

//  update_values()
//  -----------------------------------------------------------------------------------------------
/*  Initiate AJAX request for block_value options.
 */
const update_values = function ()
{
  const college = document.querySelector('input[name="college"]:checked').value;
  const block_type = document.getElementById('block-type').value;
  const period = document.querySelector('[name=period]:checked').value;
  was_selected = document.querySelector('[name=requirement-name]').value;
  console.log(college, block_type, period);
  if (college !== '' && block_type !== '')
  {
    const request = new XMLHttpRequest();
    request.addEventListener('load', values_listener);
    request.open('GET',
      `/_requirement_values/?institution=${college}&block_type=${block_type}&period=${period}`);
    request.send();
  }
  // Hide block-value and disable submit button until choices return
  document.getElementById('value-div').style.display = 'none';
  document.getElementById('institution').value = college;
};

//  main()
//  -----------------------------------------------------------------------------------------------
/*  Set up listeners
 */
const main = function ()
{
  document.getElementById('block-type').addEventListener('change', update_values);
  document.querySelectorAll('[type=radio]')
    .forEach((radio) => radio.addEventListener('change', update_values));
  document.getElementById('block-value').addEventListener('change', check_status);

  // Initial UI state
  document.getElementById('value-div').style.display = 'none';
  document.getElementById('goforit').disabled = true;
};

window.addEventListener('load', main);

