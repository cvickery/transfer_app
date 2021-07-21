
let was_selected = '';
//  check_status()
//  -----------------------------------------------------------------------------------------------
/*  Disable the submit button unless all controls have non-empty values.
 */
const check_status = function ()
{
  if (document.getElementById('institution').value === '' ||
      document.getElementById('discipline').value === '' ||
      document.getElementById('catalog_num').value === '')
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
  document.getElementById('value-div').innerHTML = this.response;
  document.getElementById('catalog_num').addEventListener('change', update_values);
  const options = document.getElementById('catalog_num').options;
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
/*  Initiate AJAX request for course-requirement mappings.
 */
const update_values = function ()
{
  const college = document.querySelector('input[name="college"]:checked').value;
  const discipline = document.getElementById('discipline').value;
  const catalog_num = document.querySelector('[name=period-range]:checked').value;
  if (college !== '' && discipline !== '' && catalog_num != '')
  {
    const request = new XMLHttpRequest();
    request.addEventListener('load', values_listener);
    const query_str = `?institution=${college}&discipline=${discipline}&catalog_num=${catalog_num}`;
    request.open('GET',
      `/_course_requirement_mappings/${query_str}`);
    request.send();
  }
  // Hide catalog_num and disable submit button until choices return
  document.getElementById('value-div').style.display = 'none';
  document.getElementById('institution').value = college;
};

//  main()
//  -----------------------------------------------------------------------------------------------
/*  Set up listeners
 */
const main = function ()
{
  document.getElementById('discipline').addEventListener('change', update_values);
  document.querySelectorAll('[type=radio]')
    .forEach(radio => radio.addEventListener('change', update_values));
  document.getElementById('catalog_num').addEventListener('change', check_status);

  // Initial UI state
  document.getElementById('value-div').style.display = 'none';
  document.getElementById('goforit').disabled = true;
};

window.addEventListener('load', main);

