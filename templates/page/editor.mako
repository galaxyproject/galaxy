<%inherit file="/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="user"
    self.overlay_visible=False
%>
</%def>

<%def name="late_javascripts()">
    <script type='text/javascript' src="${h.url_for('/static/scripts/galaxy.panels.js')}"> </script>
    <script type="text/javascript">
        ensure_dd_helper();
        ##make_left_panel( $("#left"), $("#center"), $("#left-border" ) );
        ##make_right_panel( $("#right"), $("#center"), $("#right-border" ) );
        ensure_popup_helper();
        ## handle_minwidth_hint = rp.handle_minwidth_hint;
    </script>
</%def>

<%def name="javascripts()">
    
    ${parent.javascripts()}
    
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.event.drag.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.event.drop.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.event.hover.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.form.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.jstore-all.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/json2.js')}"> </script>

    <script type='text/javascript' src="${h.url_for('/static/scripts/galaxy.base.js')}"> </script>
    
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.wymeditor.js')}"> </script>
    
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.autocomplete.js')}"> </script>
    
    <script type="text/javascript">
    ## Completely replace WYM's dialog handling
    WYMeditor.editor.prototype.dialog = function( dialogType, dialogFeatures, bodyHtml ) {
          
        var wym = this;
        var sStamp = wym.uniqueStamp();
        var selected = wym.selected();
        
        // LINK DIALOG
        if ( dialogType == WYMeditor.DIALOG_LINK ) {
            if(selected) {
                jQuery(wym._options.hrefSelector).val(jQuery(selected).attr(WYMeditor.HREF));
                jQuery(wym._options.srcSelector).val(jQuery(selected).attr(WYMeditor.SRC));
                jQuery(wym._options.titleSelector).val(jQuery(selected).attr(WYMeditor.TITLE));
                jQuery(wym._options.altSelector).val(jQuery(selected).attr(WYMeditor.ALT));
            }
            show_modal(
                "Link",
                "<div><div><label>URL</label><br><input type='text' class='wym_href' value='' size='40' /></div>"
                    + "<div><label>Title</label><br><input type='text' class='wym_title' value='' size='40' /></div><div>",
                {
                    "Make link": function() {
                        var sUrl = jQuery(wym._options.hrefSelector).val();
                        if(sUrl.length > 0) {
                  
                          wym._exec(WYMeditor.CREATE_LINK, sStamp);
                  
                          jQuery("a[href=" + sStamp + "]", wym._doc.body)
                              .attr(WYMeditor.HREF, sUrl)
                              .attr(WYMeditor.TITLE, jQuery(wym._options.titleSelector).val());
                  
                        }
                        hide_modal();
                    },
                    "Cancel:": function() {
                        hide_modal();
                    }
                }
            );
            return;
        }
        
        // IMAGE DIALOG
        if ( dialogType == WYMeditor.DIALOG_IMAGE ) {
            if(wym._selected_image) {
                jQuery(wym._options.dialogImageSelector + " " + wym._options.srcSelector)
                  .val(jQuery(wym._selected_image).attr(WYMeditor.SRC));
                jQuery(wym._options.dialogImageSelector + " " + wym._options.titleSelector)
                  .val(jQuery(wym._selected_image).attr(WYMeditor.TITLE));
                jQuery(wym._options.dialogImageSelector + " " + wym._options.altSelector)
                  .val(jQuery(wym._selected_image).attr(WYMeditor.ALT));
            }
            show_modal(
                "Image",
                "<div class='row'>"
                    + "<label>URL</label><br>"
                    + "<input type='text' class='wym_src' value='' size='40' />"
                    + "</div>"
                    + "<div class='row'>"
                    + "<label>Alt text</label><br>"
                    + "<input type='text' class='wym_alt' value='' size='40' />"
                    + "</div>"
                    + "<div class='row'>"
                    + "<label>Title</label><br>"
                    + "<input type='text' class='wym_title' value='' size='40' />"
                    + "</div>",
                {
                    "Insert": function() {  
                        var sUrl = jQuery(wym._options.srcSelector).val();
                        if(sUrl.length > 0) {
                          wym._exec(WYMeditor.INSERT_IMAGE, sStamp);
                          jQuery("img[src$=" + sStamp + "]", wym._doc.body)
                              .attr(WYMeditor.SRC, sUrl)
                              .attr(WYMeditor.TITLE, jQuery(wym._options.titleSelector).val())
                              .attr(WYMeditor.ALT, jQuery(wym._options.altSelector).val());
                        }
                        hide_modal();
                    },
                    "Cancel": function() {
                        hide_modal();
                    }
                }
            );
            return;
        }
        
        // TABLE DIALOG
        if ( dialogType == WYMeditor.DIALOG_TABLE ) {
            show_modal(
                "Table",
                "<div class='row'>"
                    + "<label>Caption</label><br>"
                    + "<input type='text' class='wym_caption' value='' size='40' />"
                    + "</div>"
                    + "<div class='row'>"
                    + "<label>Summary</label><br>"
                    + "<input type='text' class='wym_summary' value='' size='40' />"
                    + "</div>"
                    + "<div class='row'>"
                    + "<label>Number Of Rows<br></label>"
                    + "<input type='text' class='wym_rows' value='3' size='3' />"
                    + "</div>"
                    + "<div class='row'>"
                    + "<label>Number Of Cols<br></label>"
                    + "<input type='text' class='wym_cols' value='2' size='3' />"
                    + "</div>",
                {
                    "Insert": function() {
                        var iRows = jQuery(wym._options.rowsSelector).val();
                        var iCols = jQuery(wym._options.colsSelector).val();
                  
                        if(iRows > 0 && iCols > 0) {
                  
                          var table = wym._doc.createElement(WYMeditor.TABLE);
                          var newRow = null;
                                  var newCol = null;
                  
                                  var sCaption = jQuery(wym._options.captionSelector).val();
                  
                                  //we create the caption
                                  var newCaption = table.createCaption();
                                  newCaption.innerHTML = sCaption;
                  
                                  //we create the rows and cells
                                  for(x=0; x<iRows; x++) {
                                          newRow = table.insertRow(x);
                                          for(y=0; y<iCols; y++) {newRow.insertCell(y);}
                                  }
                  
                          //set the summary attr
                          jQuery(table).attr('summary',
                              jQuery(wym._options.summarySelector).val());
                  
                          //append the table after the selected container
                          var node = jQuery(wym.findUp(wym.container(),
                            WYMeditor.MAIN_CONTAINERS)).get(0);
                          if(!node || !node.parentNode) jQuery(wym._doc.body).append(table);
                          else jQuery(node).after(table);
                        }
                        hide_modal();
                    },
                    "Cancel": function() {
                        hide_modal();
                    }
                }
            );
        }
        
        // HISTORY DIALOG
        if ( dialogType == Galaxy.DIALOG_HISTORY ) {
            show_modal(
                "Insert History",
                "<div class='row'>"
                    + "<label>History Name</label><br>"
                    + "<input id='history_name_input' type='text' class='wym_galaxy_history_name' value='' size='40' />"
                    + "</div>"
                    + "<div class='row'>"
                    + "<label>Select History</label><br>"
                    + "<input type='text' class='wym_galaxy_history_selected' value='' size='40' />"
                    + "</div>"
                    ,
                    {
                    "Insert": function() {
                         var sUrl = jQuery(wym._options.hrefSelector).val();
                            if(sUrl.length > 0) {

                              wym._exec(WYMeditor.CREATE_LINK, sStamp);

                              jQuery("a[href=" + sStamp + "]", wym._doc.body)
                                  .attr(WYMeditor.HREF, sUrl)
                                  .attr(WYMeditor.TITLE, jQuery(wym._options.titleSelector).val());
                        hide_modal();
                        
                        // TODO: remove autocomplete.
                    },
                    "Cancel": function() {
                        hide_modal();
                        
                        // TODO: remove autocomplete.
                    }
                }
            );

            // Set up autocomplete for name input.
            var t = $("#history_name_input");
            var autocomplete_options = 
                { selectFirst: false, autoFill: false, highlight: false, mustMatch: false };
            t.autocomplete("${h.url_for( controller='history', action='name_autocomplete_data' )}", autocomplete_options);
        }
    };
    </script>
    
    <script type='text/javascript'>
        $(function(){
            ## Generic error handling
            $(document).ajaxError( function ( e, x ) {
                console.log( e, x );
                var message = x.responseText || x.statusText || "Could not connect to server";
                show_modal( "Server error", message, { "Ignore error" : hide_modal } );
                return false;
            });
            ## Create editor
            $("[name=page_content]").wymeditor( {
                skin: 'galaxy',
                basePath: "${h.url_for('/static/wymeditor')}/",
                iframeBasePath: "${h.url_for('/static/wymeditor/iframe/galaxy')}/",
                boxHtml:   "<table class='wym_box' width='100%' height='100%'>"
                            + "<tr><td><div class='wym_area_top'>" 
                            + WYMeditor.TOOLS
                            + WYMeditor.CONTAINERS
                            + "</div></td></tr>"
                            + "<tr height='100%'><td>"
                            + "<div class='wym_area_main' style='height: 100%;'>"
                            // + WYMeditor.HTML
                            + WYMeditor.IFRAME
                            + WYMeditor.STATUS
                            + "</div>"
                            + "</div>"
                            + "</td></tr></table>",
                toolsItems: [
                    {'name': 'Bold', 'title': 'Strong', 'css': 'wym_tools_strong'}, 
                    {'name': 'Italic', 'title': 'Emphasis', 'css': 'wym_tools_emphasis'},
                    {'name': 'Superscript', 'title': 'Superscript', 'css': 'wym_tools_superscript'},
                    {'name': 'Subscript', 'title': 'Subscript', 'css': 'wym_tools_subscript'},
                    {'name': 'InsertOrderedList', 'title': 'Ordered_List', 'css': 'wym_tools_ordered_list'},
                    {'name': 'InsertUnorderedList', 'title': 'Unordered_List', 'css': 'wym_tools_unordered_list'},
                    {'name': 'Indent', 'title': 'Indent', 'css': 'wym_tools_indent'},
                    {'name': 'Outdent', 'title': 'Outdent', 'css': 'wym_tools_outdent'},
                    {'name': 'Undo', 'title': 'Undo', 'css': 'wym_tools_undo'},
                    {'name': 'Redo', 'title': 'Redo', 'css': 'wym_tools_redo'},
                    {'name': 'CreateLink', 'title': 'Link', 'css': 'wym_tools_link'},
                    {'name': 'Unlink', 'title': 'Unlink', 'css': 'wym_tools_unlink'},
                    {'name': 'InsertImage', 'title': 'Image', 'css': 'wym_tools_image'},
                    {'name': 'InsertTable', 'title': 'Table', 'css': 'wym_tools_table'},
                ]
            });
            ## Get the editor object
            var editor = $.wymeditors(0);
            var save = function ( callback ) {
                show_modal( "Saving page", "progress" );
                $.ajax( {
                    url: "${h.url_for( action='save' )}",
                    type: "POST",
                    data: {
                        id: "${trans.security.encode_id(page.id)}",
                        content: editor.xhtml(),
                        "_": "true"
                    },
                    success: function() {
                        callback();
                    }
                });
            }
            ## Save button
            $("#save-button").click( function() {
                save( function() { hide_modal(); } )
            });
            ## Close button
            $("#close-button").click(function() {
                <% next_url = h.url_for( controller='page', action='index' ) %>
                // var new_content = editor.xhtml();
                // var changed = ( initial_content != new_content );
                var changed = false;
                if ( changed ) {
                    var do_close = function() {
                        window.onbeforeunload = undefined;
                        window.document.location = "${next_url}"
                    };
                    show_modal( "Close editor",
                                "There are unsaved changes to your page which will be lost.",
                                {
                                    "Cancel" : hide_modal,
                                    "Save Changes" : function() {
                                        save( do_close );
                                    }
                                }, {
                                    "Don't Save": do_close
                                } );
                } else {
                    window.document.location = "${next_url}";
                }
            });
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
</%def>

<%def name="center_panel()">

    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner" style="float: right">
            <a id="save-button" class="panel-header-button">Save</a>
            <a id="close-button" class="panel-header-button">Close</a>
        </div>
        <div class="unified-panel-header-inner">
            Page editor
        </div>
    </div>

    <div class="unified-panel-body">
        <textarea name="page_content">${page.latest_revision.content.decode('utf-8')}</textarea>
    </div>

</%def>
