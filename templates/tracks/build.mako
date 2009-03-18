<%inherit file="/base.mako"/>

<%def name="init()">
<%
    self.active_view="view"
    self.has_left_panel=False
%>
</%def>

<script type="text/javascript">
  setTimeout(function () {
	       window.location.reload();
	     }, 5000 );
</script>

<div class="donemessage">
<p>
Please wait while we index your tracks for viewing.  You will be
automatically redirected to choose a chromosome to view after indices
are built.
</p>
</div>
