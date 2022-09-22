/* Monitor the search-by-cip form events.
 */

async function search_programs(search_request)
{
  const request_obj = {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(search_request),
    };
  const response = await fetch('/_search_programs/', request_obj);
  return response;
}

window.addEventListener('load', function() {

  const search_text_element = document.getElementById('search_text');
  const cip_soc_span = document.getElementById('num-cip');
  search_text_element.focus();
  search_text_element.addEventListener('keyup', function(e)
  {
    // Create the query string based on element settings
    var search_request = {search_text: search_text_element.value,
                          colleges: [],
                          plans: true,
                          subplans: true}

    search_programs(search_request)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error, status = ${response.status}`);
        }
        return response.json();
      })
      .then((search_result) => {
        cip_soc_span.innerHTML = search_result['cip_codes'].length;
      });
  });
});


// async function postData(url = '', data = {}) {
//   // Default options are marked with *
//   const response = await fetch(url, {
//     method: 'POST', // *GET, POST, PUT, DELETE, etc.
//     mode: 'cors', // no-cors, *cors, same-origin
//     cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
//     credentials: 'same-origin', // include, *same-origin, omit
//     headers: {
//       'Content-Type': 'application/json'
//       // 'Content-Type': 'application/x-www-form-urlencoded',
//     },
//     redirect: 'follow', // manual, *follow, error
//     referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
//     body: JSON.stringify(data) // body data type must match "Content-Type" header
//   });
//   return response.json(); // parses JSON response into native JavaScript objects
// }

// postData('https://example.com/answer', { answer: 42 })
//   .then((data) => {
//     console.log(data); // JSON data parsed by `data.json()` call
//   });
