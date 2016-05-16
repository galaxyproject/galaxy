<%inherit file="/webapps/galaxy/base_panels.mako"/>

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
    div.historyItem {
        margin: 0px -5px;
        padding: 8px 10px;
        border-top: solid #999 1px;
        border-right: none;
        word-wrap: break-word;
        background: #EEE;
    }
    div.historyItem .state-icon {
        display: inline-block;
        vertical-align: middle;
        width: 16px;
        height: 16px;
        background-position: 0 1px;
        background-repeat: no-repeat;
    }
    div.historyItem .historyItemTitle {
        font-weight: bold;
        line-height: 16px;
    }

    .searchResult {
        border-style:dashed;
        border-width:1px;
        margin: 5px;
    }
    </style>
</%def>


<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js(
        "libs/jquery/jquery",
    )}
    <script type="text/javascript">

        function search_format_output(doc) {
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
                        _.each(data.results, search_format_output
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
                            p.append(b);
                        });
                    }
                });
            }
        };


        var queryURL = function (query) {
            var url = "/api/search" + encodeURIComponent(query);
            url = url + "&field=" + $("#searchFields").val();
            if ($("#fileType").val() != "All") {
                url = url + "&type=" +  $("#fileType").val()
            }
            return url;
        }

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
    </script>

</%def>


<%def name="center_panel()">

    <div id="search_box" style="margin: 20px;">
        <input type="text" id="search_text" size="90"/>
    </div>
    <div style="margin: 20px;">
        <input type="button" id="search_button" value="Search"/>
    </div>
    <div id="output"></div>

</%def>
