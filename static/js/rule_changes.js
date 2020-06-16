
window.addEventListener('load', function()
{
  const submit_button = document.getElementsByTagName('button')[0];
  const first_date = document.getElementById('first_date');
  const second_date = document.getElementById('second_date');

  if (submit_button)
  {
    first_date.addEventListener('change', check_ok_to_submit);
    second_date.addEventListener('change', check_ok_to_submit);
    submit_button.setAttribute('disabled', 'disabled');
  }

  function check_ok_to_submit()
  {
    if (first_date.value && second_date.value)
    {
      submit_button.removeAttribute('disabled');
    }
    else
    {
      submit_button.setAttribute('disabled', 'disabled');
    }
  }
});
