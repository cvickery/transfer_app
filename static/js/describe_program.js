// describe_program.js
/* Submit the form when either institution or programs list changes
 */

// main()
// ------------------------------------------------------------------------------------------------
const main = function()
{
  document.getElementById('lookup-program').style.opacity = 1.0;
  document.getElementById('institution'). addEventListener('change', do_submit);
  document.getElementById('program-code'). addEventListener('change', do_submit);
}

const do_submit = function()
{
  document.getElementById('lookup-program').style.opacity = 0.25;
  document.getElementById('lookup-program').requestSubmit();
}

window.addEventListener('load', main);