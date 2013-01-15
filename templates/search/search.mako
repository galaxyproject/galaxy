
<%def name="search_init()">

 ${h.js(
	'libs/jquery/jquery',
    'libs/json2'
)}

</%def>

<%def name="search_dialog()">

<script type="text/javascript">

function doSearch(query) {
	if (query.length > 1) {
		var url = "/api/search";	
		var query_struct = {};
		var domain_array = [];
		var field = $("#field_type").val();
		if (field == "name") {
			query_struct["name"] = { "$like" : "%" + $("#search_text").val() + "%" };
		}

		if ($("#history_search").val()) {
			domain_array[domain_array.length] = "history"
		}
		if ($("#history_dataset_search").val()) {
			domain_array[domain_array.length] = "history_dataset"
		}
		if ($("#library_dataset_search").val()) {
			domain_array[domain_array.length] = "library_dataset"
		}

		$.ajax({ 
			type : 'POST',
			url: url, 
			data: JSON.stringify({ "domain" : domain_array, "query" : query_struct }),
			contentType : 'application/json',
			dataType : 'json',
			success : function(data) { 
				$("#output").empty();
				var p = $("#output");
				p.empty();
				for(var i in data) {
					p.append( $("<div style='margin: 20px;'>").append(
						$("<a href='/file/" + data[i]['id'] + "'>" + data[i]['name'] + "</a>")
					)).append( 
						$("<div class='quote'>").append( 
							data[i]['name']
						)
					);
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

var suggestURL = function (query) {
	var url = "/api/search" + encodeURIComponent(query);
	url = url + "&field=" + $("#searchFields").val();
	if ($("#fileType").val() != "All") {
		url = url + "&type=" +  $("#fileType").val()
	}
	return url;	
}

var postClick = function(data) {
	$("#name").attr("value", data.data[0]);
	$("#type").attr("value", data.data[1]);	
	$("#uuid").attr("value", data.data[2]);
	document.getElementById('galaxy_form').submit();
}

var formatLink = function(doc) {
	return $("<a href='/file/" + doc['_id'] + "'>" + doc['@id'] + "</a>");
}

var formatDesc = function(doc) {
	var out = "<div>" + doc['md5'] +"</div>";
	if (doc['description'] != null) {
		return out + doc['description'].substring(0, 350)
	} else {
		return out + "<div>No Description</div>";
	}
}


</script>


<div style="margin: 20px; position: absolute; width: 100%; height: 100%">

<div id="search_box">
<input type="text" id="search_text" size="90"/>

<div align="left">
<h3>Domain</h3>
<input type="checkbox" checked="true" id="history_search">History</input><br/>
<input type="checkbox" checked="true" id="history_dataset_search">History Dataset</input><br/>
<input type="checkbox" checked="true" id="library_dataset_search">Library Dataset</input><br/>
</div>


<div>
<h3>Fields</h3>
<select id="field_type">
<option value="name">Name</a>
<option value="datatype">Data Type</a>
<option value="tag">Tags</a>
<option value="annotations">Annotations</a>
<option value="extended_metadata">Extended Metadata</a>
</select>
</div>
<div style="margin: 20px;">
<input type="button" id="search_button" value="Search"/>
</div>

<div id="output"></div>

</div>

</div>

</%def>