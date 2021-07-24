// course_mappings.js
/* clicking any radio button submits the form.
 */

// submit_form()
// ------------------------------------------------------------------------------------------------
const submit_form = function()
{
  document.getElementById('goforit').click();
};

//  main()
//  -----------------------------------------------------------------------------------------------
/*  Set up listeners
 */
const main = function ()
{
  document.querySelectorAll('[type=radio]')
    .forEach(radio => radio.addEventListener('change', submit_form));

  // Initial UI state
  // document.getElementById('goforit').disabled = true;
};

window.addEventListener('load', main);

