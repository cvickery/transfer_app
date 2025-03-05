document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('need-js').style.display = 'none';

    // Get form elements
    const institution = document.getElementById('institution-select');
    const discipline = document.getElementById('discipline-select');
    const catalog_nbr = document.getElementById('course-select');

    // If institution changes, clear the discipline and catalog_nbr, and submit the form.
    institution.addEventListener('change', () => {
      discipline.value = '';
      catalog_nbr.value = '';
      institution.form.submit();
    });

    // If discipline changes. clear the catalog_nbr, and submit the form
    discipline.addEventListener('change', () => {
      catalog_nbr.value = '';
      discipline.form.submit();
    });

    // If catalog_nbr changes, just submit the form.
    catalog_nbr.addEventListener('change', () => {
      catalog_nbr.form.submit();
    });

});
