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
</style>
</%def>

<%def name="center_panel()">
<div id="content">
    <div id="top-labeltrack"></div>
    <div id="viewport-container" style="overflow-x: hidden; overflow-y: auto;">
        <div id="viewport"></div>
    </div>
    
</div>
<div id="nav-container" style="width:100%;">
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
            <input type="hidden" name="id" value="${config.get('vis_id', '')}" />
                <a href="#" onclick="javascript:view.zoom_in();view.redraw();">
                    <img src="${h.url_for('/static/images/fugue/magnifier-zoom.png')}" />
                </a>
                <a href="#" onclick="javascript:view.zoom_out();view.redraw();">
                    <img src="${h.url_for('/static/images/fugue/magnifier-zoom-out.png')}" />
                </a>
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
##        <input name="title" id="title" value="${config.title}" />
        <div id="show-hide-move">
            <ul id="sortable-ul"></ul>
        </div>
        <input type="button" id="refresh-button" value="Refresh" />
        <input type="button" id="save-button" value="Save" />
        <input id="add-track" type="button" value="Add Track" />
    </form>

</%def>

<%def name="javascripts()">
${parent.javascripts()}
${h.js( 'galaxy.base', 'galaxy.panels', "json2", "jquery", "jquery.event.drag", "jquery.mousewheel", "trackster", "ui.core", "ui.sortable" )}

<script type="text/javascript">

    var data_url = "${h.url_for( action='data' )}";
    var view;
    
    $(function() {
        
        %if config:
            view = new View( "${config.get('chrom')}", "${config.get('title') | h}", "${config.get('vis_id')}", "${config.get('dbkey')}" );
            %for track in config.get('tracks'):
                view.add_track( 
                    new ${track["track_type"]}( "${track['name'] | h}", ${track['dataset_id']}, ${track['prefs']} ) 
                );
            %endfor
            init();
        %else:
            continue_fn = function() {
                view = new View( undefined, $("#new-title").val(), undefined, $("#new-dbkey").val() );
                init();
                hide_modal();
            };
            $.ajax({
                url: "${h.url_for( action='new_browser' )}",
                data: {},
                error: function() { alert( "Couldn't create new browser" ) },
                success: function(form_html) {
                    show_modal("New Track Browser", form_html, {
                        "Cancel": function() { window.location = "/"; },
                        "Continue": continue_fn
                    });
                    $("#new-title").focus();
                }
            });
        %endif
        
        // Execute this when everything is ready
        function init() {
            $("ul#sortable-ul").sortable({
                update: function(event, ui) {
                    for (var track_id in view.tracks) {
                        var track = view.tracks[track_id];
                    }
                }
            });
            
            $(document).bind( "redraw", function( e ) {
                view.redraw();
            });

            $("#content").bind("mousewheel", function( e, delta ) {
                if (delta > 0) {
                    view.zoom_in(e.pageX, $("#viewport-container"));
                } else {
                    view.zoom_out();
                }
                e.preventDefault();
            });

            $("#content").bind("dblclick", function( e ) {
                view.zoom_in(e.pageX, $("#viewport-container"));
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
                                $('input[name=id]:checked').each(function() {
                                    var item_id = $(this).val();
                                    $.ajax( {
                                        url: "${h.url_for( action='add_track_async' )}",
                                        data: { id: item_id },
                                        dataType: "json",
                                        error: function() {},
                                        success: function(track_data) {
                                            var new_track;
                                            var td = track_data;
                                            switch(track_data.track_type) {
                                                case "LineTrack":
                                                    new_track = new LineTrack( track_data.name, track_data.dataset_id, track_data.prefs );
                                                    break;
                                                case "FeatureTrack":
                                                    new_track = new FeatureTrack( track_data.name, track_data.dataset_id, track_data.prefs );
                                                    break;
                                                case "ReadTrack":
                                                    new_track = new ReadTrack( track_data.name, track_data.dataset_id, track_data.prefs );
                                                    break;
                                            }
                                            view.add_track(new_track);
                                            sidebar_box(new_track);
                                        }
                                    });

                                });
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
                        "name": track.name,
                        "dataset_id": track.dataset_id,
                        "prefs": track.prefs
                    });
                }
                // Show saving dialog box
                show_modal("Saving...", "<img src='${h.url_for('/static/images/yui/rel_interstitial_loading.gif')}'/>");
                
                $.ajax({
                    url: "${h.url_for( action='save' )}",
                    data: {
                        'vis_id': view.vis_id,
                        'vis_title': view.title,
                        'dbkey': view.dbkey,
                        'payload': JSON.stringify(payload)
                    },
                    success: function(vis_id) {
                        view.vis_id = vis_id;
                        hide_modal();
                    }
                });
            });
            
            view.add_label_track( new LabelTrack( $("#top-labeltrack" ) ) );
            view.add_label_track( new LabelTrack( $("#nav-labeltrack" ) ) );
            
            $.getJSON( "${h.url_for( action='chroms' )}", { dbkey: view.dbkey }, function ( data ) {
                view.chrom_data = data;
                var chrom_options = '<option value="">Select Chrom/Contig</option>';
                for (i in data) {
                    var chrom = data[i]['chrom']
                    chrom_options += '<option value="' + chrom + '">' + chrom + '</option>';
                }
                $("#chrom").html(chrom_options);
                $("#chrom").bind( "change", function () {
                    view.chrom = $("#chrom").val();
                    var found = $.grep(view.chrom_data, function(v, i) {
                        return v.chrom === view.chrom;
                    })[0];
                    view.max_high = found.len;
                    view.reset();
                    view.redraw(true);
                    
                    for (var track_id in view.tracks) {
                        var track = view.tracks[track_id];
                        if (track.init) {
                            track.init();
                        }
                    }
                    view.redraw();
                });
            });
            
            function sidebar_box(track) {
                if (!track.hidden) {
                    var track_id = track.track_id,
                        label = $('<label for="track_' + track_id + 'title">' + track.name + '</label>'),
                        title = $('<div class="historyItemTitle"></div>'),
                        icon_div = $('<div class="historyItemButtons"></div>');
                        del_icon = $('<a href="#" class="icon-button delete" />'),
                        edit_icon = $('<a href="#" class="icon-button edit" />'),
                        body = $('<div class="historyItemBody"></div>'),
                        li = $('<li class="sortable"></li>').attr("id", "track_" + track_id),
                        div = $('<div class="historyItemContainer historyItem"></div>'),
                        editable = $('<div style="display:none"></div>').attr("id", "track_" + track_id + "_editable");
                    
                    edit_icon.bind("click", function() {
                        $("#track_" + track_id + "_editable").toggle();
                    });
                    
                    del_icon.bind("click", function() {
                        li.fadeOut('slow', function() { $(this).remove(); });
                        view.remove_track(track);
                        view.update_options();
                    });
                    icon_div.append(edit_icon).append(del_icon);
                    title.append(label).prepend(icon_div);
                    if (track.gen_options) {
                        editable.append(track.gen_options(track_id)).appendTo(body);
                    }
                    div.append(title).append(body).appendTo(li)
                    $("ul#sortable-ul").append(li);
                }
            };
            
            // Populate sort/move ul
            for (var track_id in view.tracks) {
                var track = view.tracks[track_id];
                sidebar_box(track);
            }
            
            $(window).trigger("resize");
        };
        
    });

</script>
</%def>

