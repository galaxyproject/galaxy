<%inherit file="/form.mako"/>

<%def name="javascripts()">
${parent.javascripts()}
<script type="text/javascript">
$(function(){
    var visualization_name = $("input[name=visualization_title]");
    var visualization_slug = $("input[name=visualization_slug]");
    visualization_name.keyup(function(){
        visualization_slug.val( $(this).val().replace(/\s+/g,'-').replace(/[^a-zA-Z0-9\-]/g,'').toLowerCase() )
    });    
})
</script>
</%def>