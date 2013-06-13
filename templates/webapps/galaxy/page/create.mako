<%inherit file="/form.mako"/>

<%def name="javascripts()">
${parent.javascripts()}
<script type="text/javascript">
$(function(){
    var page_name = $("input[name=page_title]");
    var page_slug = $("input[name=page_slug]");
    page_name.keyup(function(){
        page_slug.val( $(this).val().replace(/\s+/g,'-').replace(/[^a-zA-Z0-9\-]/g,'').toLowerCase() )
    });    
})
</script>
</%def>