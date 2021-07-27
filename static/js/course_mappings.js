// course_mappings.js
/* clicking any radio button submits the form.
 */

// submit_form()
// ------------------------------------------------------------------------------------------------
const submit_form = function()
{
  document.getElementById('goforit').click();
};


// slider_change()
// ------------------------------------------------------------------------------------------------
const slider_change = function(event)
{
  const values = [
    1,
    2,
    5,
    10,
    20,
    50,
    100,
    'all'
  ];
  const slider_val = document.querySelector('#slider + span');
  slider_val.innerText = values[event.target.value];
};


//  main()
//  -----------------------------------------------------------------------------------------------
/*  Set up listeners
 */
const main = function ()
{
  document.querySelectorAll('[type=radio]')
    .forEach(radio => radio.addEventListener('change', submit_form));

  const slider_element = document.getElementById('slider');
  slider_element.addEventListener('change', slider_change);
  slider_change({target: slider_element})
};

window.addEventListener('load', main);

