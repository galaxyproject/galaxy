<%inherit file="/base.mako"/>

<%def name="init()">
<%
    self.active_view="view"
    self.has_left_panel=False
%>
</%def>

<div class="form">
  <div class="form-title">Select Chromosome/Contig/Scaffold/etc.</div>
  <div id="dbkey" class="form-body">
    <form action="/tracks/index" method="GET" target="_parent">
      <div class="form-row">
	<label for="dbkey">Chrom: </label>
	<div class="form-row-input">
	  <select name="chrom" id="chrom">
	    %for chrom in data_resource:
	    <option value="${chrom}">${chrom}</option>
	    %endfor
	  </select>
	</div>
	<div style="clear: both;"></div>
      </div>
      <div class="form-row">
	<input type="submit" value="View" />
      </div>
    </form>    
  </div>
</div>
