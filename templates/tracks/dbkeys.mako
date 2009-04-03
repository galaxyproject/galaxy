<%inherit file="/base.mako"/>

<%def name="init()">
<%
    self.active_view="view"
    self.has_left_panel=False
%>
</%def>

<div class="form">
  <div class="form-title">Select DBKey</div>
  <div id="dbkey" class="form-body">
    <form action="/tracks/list" method="GET">
      <div class="form-row">
	<label for="dbkey">DBKey: </label>
	<div class="form-row-input">
	  <select name="dbkey" id="dbkey">
	    %for dbkey in data_resource:
	    <option value="${dbkey}">${dbkey}</option>
	    %endfor
	  </select>
	</div>
	<div style="clear: both;"></div>
      </div>
      <div class="form-row">
	<input type="submit" value="Select Datasets..."/>
      </div>
    </form>    
  </div>
</div>
