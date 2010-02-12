<%inherit file="/base.mako"/>
<%def name="title()">Launching Display Application: ${display_link.link.display_application.name}  ${display_link.link.name}</%def>

<script type="text/javascript">  
    location.href = '${display_link.display_url()}';
</script>
<p>
All data has been prepared for the external display application: ${display_link.link.display_application.name}  ${display_link.link.name}.
</p>
<p>
You are now being automatically forwarded to the external application.
</p>
<p>
Click <a href="${display_link.display_url()}">here</a> if this redirect has failed.
</p>
