<%inherit file="/base.mako"/>

<%def name="init()">
<%
    self.active_view="view"
    self.has_left_panel=False
%>
</%def>

<div class="form">
  <div class="form-title">Select Datasets to View</div>
  <div id="dbkey" class="form-body">
    <form action="/tracks/build" method="GET">
      %for key,value in data_resource.items():
      <div class="form-row">
	<label for="${key}">${value}</label>
	<div class="form-row-input">
	  <input type="checkbox" name="${key}" />
	</div>
	<div style="clear: both;"></div>
      </div>
      %endfor
      <div class="form-row">
	<input type="submit" value="Build..." />
      </div>
    </form>    
  </div>
</div>
