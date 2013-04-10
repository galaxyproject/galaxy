
<%inherit file="/webapps/galaxy/base_panels.mako"/>
<%namespace file="/search/search.mako" import="search_init" />
<%namespace file="/search/search.mako" import="search_dialog" />

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
    self.active_view="shared"
    self.overlay_visible=False
%>
</%def>

<%def name="stylesheets()">
${parent.stylesheets()}
<style>
.searchResult {
	border-style:dashed;
	border-width:1px;
	margin: 5px;
}
</style>

</%def>

<%def name="center_panel()">
${search_init()}

<script type="text/javascript">
var search_format_output = function(doc) {
	var div_class = "historyItem";
	var a = $("<div class='" + div_class + "'>")
	a.append($("<div>").append(doc['model_class']));
	b = a.append( $("<div class='historyItemTitle'><a href='/file/" + doc['id'] + "'>" + doc['name'] + "</a></div>") );
	if ('misc_blurb' in doc) {
		b.append( $("<div>").append(doc["misc_blurb"]) );
	}
	if ('peek' in doc) {
		b.append( $("<pre class='peek'>").append( doc["peek"]) );
	}
	return a;
}

</script>
<div style="overflow: auto; height: 100%">
${search_dialog("search_format_output")}
</div>
</%def>


