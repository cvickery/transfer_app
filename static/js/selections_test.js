// Log form submission events

async function record_form_data(formObject)
{
  const request_obj = {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(formObject),
  };

  const request = new Request('/_log_submits/', request_obj);
  fetch(request).then((response) =>
  {
    if (!response.ok)
    {
      console.log('Oh no!', response.status);
    }
  })
}


window.addEventListener('load', function()
{
  const forms_list = document.getElementsByTagName('form');
  for (form of forms_list)
  {
    form.addEventListener('submit', function(event)
    {
      formData = new FormData(form);
      formObject = {'pathname': window.location.pathname};
      var key = encodeURIComponent('pathname');
      var value = encodeURIComponent(window.location.pathname);
      var params = [key+'='+value];
      for (entry of formData.entries())
      {
        key = encodeURIComponent(entry[0]);
        value = encodeURIComponent(entry[1])
        params.push('&'+key+'='+value);
      }
      var request = new XMLHttpRequest();
      request.open('POST', '/_log_submits/', true);
      request.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
      request.send(params);
    });
  }
});