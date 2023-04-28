// Log form submission events
/*  Find all form elements on this web page.
 *  Whenever a form is submitted, send the name of this web page, plus all the form’s name-value
 *  pairs to the server, where they can be logged to a db table.
 */
window.addEventListener('load', function()
{
  const forms_list = document.getElementsByTagName('form');
  for (form of forms_list)
  {
    form.addEventListener('submit', function(event)
    {
      let params = `pathname=${window.location.pathname}`;
      let formData = new FormData(form);
      for (entry of formData.entries())
      {
        params += `&${entry[0]}=${entry[1]}`;
      }
      const request = new XMLHttpRequest();
      request.open('POST', '/_log_submits/', false);
      request.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
      request.send(params);
    });
  }
});