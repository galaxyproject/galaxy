
<%def name="search_init()">

 ${h.js(
	'libs/jquery/jquery',
)}

</%def>

<%def name="search_dialog(output_format)">

<script type="text/javascript">

function doSearch(query) {
	if (query.length > 1) {
		var url = "/api/search";
		$.ajax({
			type : 'POST',
			url: url,
			data: JSON.stringify({"query" : query }),
			contentType : 'application/json',
			dataType : 'json',
			success : function(data) {
				var p = $("#output");
				p.empty();
				for(var i in data) {
					var e = ${output_format}(data[i]);
					p.append(e);
				}
			}
		});
	}
};

$(document).ready( function() {
	$("#search_button").click(function() {
		doSearch($("#search_text").val());
	});
	$('#search_text').keyup(function(e){
		if(e.keyCode == 13) {
			doSearch($("#search_text").val());
		}
	});
	doSearch($("#search_text").val());
});

var queryURL = function (query) {
	var url = "/api/search" + encodeURIComponent(query);
	url = url + "&field=" + $("#searchFields").val();
	if ($("#fileType").val() != "All") {
		url = url + "&type=" +  $("#fileType").val()
	}
	return url;
}

</script>

<div id="search_box" style="margin: 20px;">
	<input type="text" id="search_text" size="90"/>
</div>
<div style="margin: 20px;">
	<input type="button" id="search_button" value="Search"/>
</div>

<div id="output"></div>


</%def>
