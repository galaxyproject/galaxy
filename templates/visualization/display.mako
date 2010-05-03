<%inherit file="/display_base.mako"/>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "jquery.event.drag", "jquery.autocomplete", "jquery.mousewheel", "trackster", "ui.core", "ui.sortable" )}
    
    ## HACK: set config as item_data.
    <% config = item_data %>
    
    ## TODO: Copied from browser.mako -- probably should create JS file for visualization code and include visualization JS above.
    <script type="text/javascript">

        ## JG: add controller name.
        var data_url = "${h.url_for( controller='/tracks', action='data' )}";
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
                            "Continue": function() { $(document).trigger("convert_dbkeys"); continue_fn(); }
                        });
                        $("#new-title").focus();
                        replace_big_select_inputs();
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
                    $("#viewport-container").height( $(window).height() - 120 );
                    $("#nav-container").width( $("#center").width() );
                    view.redraw();
                };
                $(window).bind( "resize", function(e) { refresh(e); } );
                $("#right-border").bind( "click", function(e) { refresh(e); } );
                $("#right-border").bind( "dragend", function(e) { refresh(e); } );
                $(window).trigger( "resize" );

                $("#viewport-container").bind( "dragstart", function( e ) {
                    this.original_low = view.low;
                    this.current_height = e.clientY;
                    this.current_x = e.offsetX;
                }).bind( "drag", function( e ) {
                    var container = $(this);
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
                
                ## JG: Removed 'add-track' init code.
                
                ## JG: Removed 'save-button' init code

                view.add_label_track( new LabelTrack( $("#top-labeltrack" ) ) );
                view.add_label_track( new LabelTrack( $("#nav-labeltrack" ) ) );

                $.ajax({
                    ## JG: added controller name
                    url: "${h.url_for( controller='/tracks', action='chroms' )}", 
                    data: { vis_id: view.vis_id },
                    dataType: "json",
                    success: function ( data ) {
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
                    },
                    error: function() {
                        alert( "Could not load chroms for this dbkey:", view.dbkey );
                    }
                });

                ## JG: Removed function sidebar_box() and sidebar init code.

                $(window).trigger("resize");
            };

        });

    </script>
    
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

<%def name="render_item_links( visualization )">
    ## TODO
</%def>

<%def name="render_item( visualization, config )">
    <br><br>
    ## Copied from center_panel() in browser.mako -- probably need to create visualization_common.mako to render view.
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
                <form action="#">
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