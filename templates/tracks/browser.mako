<%inherit file="/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=True
    self.active_view="visualization"
    self.message_box_visible=False
%>
</%def>

<%def name="stylesheets()">
${parent.stylesheets()}

${h.css( "history" )}
<link rel="stylesheet" type="text/css" href="${h.url_for('/static/trackster.css')}" />
<style type="text/css">
    ul#sortable-ul {
        list-style: none;
        padding: 0;
        margin: 5px;
    }
    ul#sortable-ul li {
        display: block;
        margin: 5px 0;
        background: #eee;
    }
    .delete-button {
        background: transparent url(history-buttons.png) no-repeat scroll 0 -104px;
        height: 20px;
        width: 20px;
    }
    .delete-button:hover {
        background-position: 0 -130px;
    }

</style>
</%def>

<%def name="center_panel()">
<div id="content">
    <div id="top-labeltrack"></div>
    <div id="viewport-container" style="overflow-x: hidden; overflow-y: auto;">
        <div id="viewport"></div>
    </div>
    
</div>
<div id="nav-container">
    <div id="nav-labeltrack"></div>
    <div id="nav">
        <div id="overview">
            <div id="overview-viewport">
                <div id="overview-box"></div>
            </div>
        </div>
        <div id="nav-controls">
            <form name="chr" id="chr" method="get">
                <select id="chrom" name="chrom" style="width: 15em;">
                    <option value="">Loading</option>
                </select>
            <input id="low" size="12" />:<input id="high" size="12" />
                ## <input type="hidden" name="dataset_ids" value="${dataset_ids}" />
            <input type="hidden" name="id" value="${id}" />
                <a href="#" onclick="javascript:view.zoom_in();view.redraw();">+</a>
                <a href="#" onclick="javascript:view.zoom_out();view.redraw();">-</a>
            </form>
            <div id="debug" style="float: right"></div>
        </div>
    </div>
</div>
</%def>

<%def name="right_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">Configuration</div>
    </div>
    <form action="${h.url_for( action='update_config' )}">
##        <input name="title" id="title" value="${title}" />
        <div id="show-hide-move">
            <ul id="sortable-ul"></ul>
        </div>
##      <input type="submit" id="update-config" value="Save settings" />
        <input type="button" id="refresh-button" value="Refresh" />
        <input type="button" id="save-button" value="Save" />
        <input id="add-track" type="button" value="Add Track" />
    </form>

</%def>

<%def name="javascripts()">
${parent.javascripts()}
${h.js( "json2", "jquery", "jquery.event.drag", "jquery.mousewheel", "trackster", "ui.core", "ui.sortable" )}

<script type="text/javascript">

    var data_url = "${h.url_for( action='data' )}";
    var view = new View( "${chrom}", ${LEN} );
    
    $(function() {
        
        view.add_track( new LabelTrack( $("#top-labeltrack" ) ) );
        view.add_track( new LabelTrack( $("#nav-labeltrack" ) ) );
   
        %for track in tracks:
            view.add_track( 
                new ${track["track_type"]}( "${track['name']}", ${track['dataset_id']}, "${track['indexer']}", ${track['prefs']} ) 
            );
        %endfor
        
        $(document).bind( "redraw", function( e ) {
            view.redraw();
        });
        
        $("#content").bind("mousewheel", function( e, delta ) {
            if (delta > 0) {
                view.zoom_in(e.pageX);
            } else {
                view.zoom_out();
            }
            e.preventDefault();
        });
        
        $("#content").bind("dblclick", function( e ) {
            view.zoom_in(e.pageX);
        });
        
        // To let the overview box be draggable
        $("#overview-box").bind("dragstart", function( e ) {
            this.current_x = e.offsetX;
        }).bind("drag", function( e ) {
            var delta = e.offsetX - this.current_x;
            this.current_x = e.offsetX;
            
            var delta_chrom = Math.round(delta / $(document).width() * view.span);
            view.center += delta_chrom;
            view.redraw();
        });

        // To adjust the size of the viewport to fit the fixed-height footer
        var refresh = function( e ) {
            $("#content").height( $(window).height() - $("#nav-container").height() - $("#masthead").height());
            $("#viewport-container").height( $("#content").height() - $("#top-labeltrack").height() - $("#nav-labeltrack").height() );
            $("#nav-container").width( $("#center").width() );
            view.redraw();
        };
        $(window).bind( "resize", function(e) { refresh(e); } );
        $("#right-border").bind( "click", function(e) { refresh(e); } );
        $("#right-border").bind( "dragend", function(e) { refresh(e); } );
        $(window).trigger( "resize" );

        $("#viewport").bind( "dragstart", function( e ) {
            this.original_low = view.low;
            this.current_height = e.clientY;
            this.current_x = e.offsetX;
        }).bind( "drag", function( e ) {
            var container = $(this).parent();
            var delta = e.offsetX - this.current_x;
            var new_scroll = container.scrollTop() - (e.clientY - this.current_height);
            if ( new_scroll < container.get(0).scrollHeight - container.height() ) {
                container.scrollTop(new_scroll);
            }
            this.current_height = e.clientY;
            this.current_x = e.offsetX;

            var delta_chrom = Math.round(delta / $(document).width() * (view.high - view.low));
            view.center -= delta_chrom;
            view.redraw();
        });
        
        $("#refresh-button").bind( "click", function(e) {
            view.update_options();
        });
        
        // Use a popup grid to add more tracks
        $("#add-track").bind( "click", function(e) {
            $.ajax({
                url: "${h.url_for( action='list_datasets' )}",
                data: {},
                error: function() { alert( "Grid refresh failed" ) },
                success: function(table_html) {
                    show_modal("Add Track &mdash; Select Dataset(s)", table_html, {
                        "Insert": function() {
                            hide_modal();
                        },
                        "Cancel": function() {
                            hide_modal();
                        }
                    });
                }
            });
        });
        
        $("#save-button").bind("click", function(e) {
            view.update_options();
            var sorted = $("ul#sortable-ul").sortable('toArray');
            var payload = [];
            for (var i in sorted) {
                var track_id = parseInt(sorted[i].split("track_")[1]),
                    track = view.tracks[track_id];
                
                payload.push( {
                    "track_type": track.track_type,
                    "indexer": track.indexer,
                    "name": track.name,
                    "dataset_id": track.dataset_id,
                    "prefs": track.prefs
                });
            }
            $.ajax({
                url: "${h.url_for( action='save' )}",
                data: {
                    'id': '${id}',
                    'payload': JSON.stringify(payload)
                }
            });
        });
        
        // Execute this on page load
        (function () {
            $.getJSON( "${h.url_for( action='chroms' )}", { dbkey: "${dbkey}" }, function ( data ) {
                var chrom_options = '<option value="">Select Chrom/Contig</option>';
                for (i in data) {
                    chrom = data[i]['chrom']
                    if( chrom == view.chrom ) {
                        chrom_options += '<option value="' + chrom + '" selected="true">' + chrom + '</option>';                  
                    } else {
                        chrom_options += '<option value="' + chrom + '">' + chrom + '</option>';
                    }
                }
                $("#chrom").html(chrom_options);
                $("#chrom").bind( "change", function () {
                    $("#chr").submit();
                });
            });
            
            // Populate sort/move ul
            for (var track_id in view.tracks) {
                var track = view.tracks[track_id];
                if (!track.hidden) {
                    var label = $('<label for="track_' + track_id + 'title">' + track.name + '</label>');
                    var title = $('<div class="historyItemTitle"></div>');
                    var del_icon = $('<a style="display:block; float:right" href="#" class="icon-button delete" />');
                    var body = $('<div class="historyItemBody"></div>');
                    // var checkbox = $('<input type="checkbox" checked="checked"></input>').attr("id", "track_" + track_id + "title");
                    var li = $('<li class="sortable"></li>').attr("id", "track_" + track_id);
                    var div = $('<div class="historyItemContainer historyItem"></div>');
                    del_icon.prependTo(title);
                    label.appendTo(title);
                    // checkbox.prependTo(title);
                    if (track.gen_options) {
                        body.append(track.gen_options(track_id));
                    }
                    title.prependTo(div);
                    body.appendTo(div);
                    li.append(div);
                    $("ul#sortable-ul").append(li);
                }
            }
            
            $("ul#sortable-ul").sortable({
                update: function(event, ui) {
                    for (var track_id in view.tracks) {
                        var track = view.tracks[track_id];
                    }
                }
            });
            
        })();
        $(window).trigger("resize");
    });

</script>
</%def>

