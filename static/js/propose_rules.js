$(function ()
{
  var src_institution, dst_institution;
  $('#need-js').hide();
  $('#src_institution').change(function ()
    {
      src_institution = $(this).val();
      console.log(src_institution);
    });
});
