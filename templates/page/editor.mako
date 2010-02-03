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
    ${h.js( "jquery", "jquery.event.drag", "jquery.event.drop", "jquery.event.hover", "jquery.form", "jquery.jstore-all", "json2", 
            "galaxy.base", "jquery.wymeditor", "jquery.autocomplete", "autocomplete_tagging")}    
    <script type="text/javascript">
            
    // Useful Galaxy stuff.
    var Galaxy = 
    {
        DIALOG_HISTORY_LINK : "history_link",
        DIALOG_DATASET_LINK : "dataset_link",
        DIALOG_WORKFLOW_LINK : "workflow_link",
        DIALOG_PAGE_LINK : "page_link",
        DIALOG_HISTORY_ANNOTATE : "history_annotate",
    };
    
    // Initialize Galaxy elements.
    function init_galaxy_elts(wym) 
    {
        // Set up events to make annotation easy.
        $('.annotation', wym._doc.body).each( function() 
        {
             $(this).click( function() {
                 // Works in Safari, not in Firefox.
                 var range = wym._doc.createRange();
                 range.selectNodeContents( this );
                 var selection = window.getSelection();
                 selection.removeAllRanges();
                 selection.addRange(range);
                 var t = "";
             });
        });
        
    };
    
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
        
        // INSERT "GALAXY ITEM" (HISTORY, DATASET, WORKFLOW, PAGE) LINK DIALOG
        if ( dialogType == Galaxy.DIALOG_HISTORY_LINK || dialogType == Galaxy.DIALOG_DATASET_LINK || 
             dialogType == Galaxy.DIALOG_WORKFLOW_LINK || dialogType == Galaxy.DIALOG_PAGE_LINK ) {
            // Based on item type, set useful vars.
            var 
                item_singular, 
                item_plural, 
                item_controller,
                item_list_action;
            switch( dialogType ) {
                case( Galaxy.DIALOG_HISTORY_LINK ):
                    item_singular = "History";
                    item_plural = "Histories";
                    item_controller = "history"
                    break;
                case( Galaxy.DIALOG_DATASET_LINK ):
                    item_singular = "Dataset";
                    item_plural = "Datasets";
                    item_controller = "dataset"
                    break;
                case( Galaxy.DIALOG_WORKFLOW_LINK ):
                    item_singular = "Workflow";
                    item_plural = "Workflows";
                    item_controller = "workflow"
                    break;
                case( Galaxy.DIALOG_PAGE_LINK ):
                    item_singular = "Page";
                    item_plural = "Pages";
                    item_controller = "page"
                break;
            }
            item_list_action = "list_" + item_plural.toLowerCase() + "_for_selection";
            
            // Show grid that enables user to select items.
            var url_template = "${h.url_for( action='LIST_ACTION' )}";
            var ajax_url = url_template.replace( "LIST_ACTION", item_list_action );
            $.ajax(
            {
                url: ajax_url,
                data: {},
                error: function() { alert( "Failed to list "  + item_plural.toLowerCase() + " for selection"); },
                success: function(table_html) 
                {
                    show_modal(
                        "Insert Link to " + item_singular,
                        table_html +
                        "<div><input id='make-importable' type='checkbox' checked/>" +
                        "Make the selected " + item_plural.toLowerCase() + " accessible so that they can viewed by everyone.</div>"
                        ,
                        {
                            "Insert": function() 
                            {
                                // Make items accessible (importable) ?
                                var make_importable = false;
                                if ( $('#make-importable:checked').val() !== null )
                                    make_importable = true;
                                
                                // Insert links to history for each checked item.
                                var item_ids = new Array();
                                $('input[name=id]:checked').each(function() {
                                    var item_id = $(this).val();
                                    
                                    // Make history importable?
                                    if (make_importable)
                                    {
                                        url_template = "${h.url_for( controller='ITEM_CONTROLLER', action='set_accessible_async' )}";
                                        ajax_url = url_template.replace( "ITEM_CONTROLLER", item_controller);
                                        $.ajax({
                                          type: "POST",
                                          url: ajax_url,
                                          data: { id: item_id, accessible: 'True' },
                                          error: function() { alert("Making " + item_plural.toLowerCase() + " accessible failed"); }
                                        });
                                    }
                                    
                                    // Insert link(s) to item(s). This is done by getting item info and then manipulating wym.
                                    url_template = "${h.url_for( controller='ITEM_CONTROLLER', action='get_name_and_link_async' )}?id=" + item_id;
                                    ajax_url = url_template.replace( "ITEM_CONTROLLER", item_controller);
                                    $.getJSON( ajax_url, function( item_info ) {
                                        // Get link text.
                                        wym._exec(WYMeditor.CREATE_LINK, sStamp);
                                        var link_text = $("a[href=" + sStamp + "]", wym._doc.body).text();
                                        
                                        // Insert link: need to do different actions depending on link text.
                                        if (
                                            link_text == "" // Firefox.
                                            ||
                                            link_text == sStamp // Safari
                                            )
                                        {
                                            // User selected no text; create link from scratch and use default text.
                                            wym.insert("<a href='" + item_info.link + "'> '" + item_singular + " " + item_info.name + "'</a>");
                                        }
                                        else
                                        {
                                            // Link created from selected text; add href and title.
                                            $("a[href=" + sStamp + "]", wym._doc.body).attr(WYMeditor.HREF, item_info.link).attr(WYMeditor.TITLE, item_singular + item_id);
                                        }
                                    });                                    
                                });
                                
                                hide_modal();
                            },
                            "Cancel": function() 
                            {
                                hide_modal();
                            }
                        }
                    );
                }
            });
        }
        // ANNOTATE HISTORY DIALOG
        if ( dialogType == Galaxy.DIALOG_ANNOTATE_HISTORY ) {
            $.ajax(
            {
                url: "${h.url_for( action='list_histories_for_selection' )}",
                data: {},
                error: function() { alert( "Grid refresh failed" ) },
                success: function(table_html) 
                {
                    show_modal(
                        "Insert Link to History",
                        table_html,
                        {
                            "Annotate": function() 
                            {
                                // Insert links to history for each checked item.
                                var item_ids = new Array();
                                $('input[name=id]:checked').each(function() {
                                    var item_id = $(this).val();
                                    
                                    // Get annotation table for history.
                                    $.ajax(
                                    {
                                        url: "${h.url_for( action='get_history_annotation_table' )}",
                                        data: { id : item_id },
                                        error: function() { alert( "Grid refresh failed" ) },
                                        success: function(result) 
                                        {
                                            // Insert into document.
                                            wym.insert(result);
                                            
                                            init_galaxy_elts(wym);

                                        }
                                    });                                    
                                });
                                
                                hide_modal();
                            },
                            "Cancel": function() 
                            {
                                hide_modal();
                            }
                        }
                    );
                }
            });
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
                    {'name': 'Insert Galaxy History Link', 'title' : 'Galaxy_History_Link', 'css' : 'galaxy_tools_insert_history_link'},
                    {'name': 'Insert Galaxy Dataset Link', 'title' : 'Galaxy_Dataset_Link', 'css' : 'galaxy_tools_insert_dataset_link'},
                    {'name': 'Insert Galaxy Workflow Link', 'title' : 'Galaxy_Workflow_Link', 'css' : 'galaxy_tools_insert_workflow_link'},
                    {'name': 'Insert Galaxy Page Link', 'title' : 'Galaxy_Page_Link', 'css' : 'galaxy_tools_insert_page_link'},
                    {'name': 'Annonate Galaxy History', 'title' : 'Annotate_Galaxy_History', 'css' : 'galaxy_tools_annotate_history'},
                ]
            });
            ## Get the editor object
            var editor = $.wymeditors(0);
            var save = function ( callback ) {
                show_modal( "Saving page", "progress" );
                // Gather annotations.
                var annotations = new Array();
                
                $('.annotation', editor._doc.body).each( function() {
                    var item_class = $(this).attr( 'item_class' );
                    var item_id = $(this).attr( 'item_id' );
                    var text = $(this).text();
                    annotation = {
                        "item_class" : item_class,
                        "item_id" : item_id,
                        "text" : text
                    };
                    annotations[ annotations.length ] = annotation;
                });
                
                // Do save.
                $.ajax( {   
                    url: "${h.url_for( action='save' )}",
                    type: "POST",
                    data: {
                        id: "${trans.security.encode_id(page.id)}",
                        content: editor.xhtml(),
                        annotations: JSON.stringify(annotations),
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
                <% next_url = h.url_for( controller='page', action='list' ) %>
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
            
            // Initialize 'Insert history link' button.
            $('.galaxy_tools_insert_history_link').children().click( function() {
                editor.dialog(Galaxy.DIALOG_HISTORY_LINK); 
            });
            // Initialize 'Insert dataset link' button.
            $('.galaxy_tools_insert_dataset_link').children().click( function() {
                editor.dialog(Galaxy.DIALOG_DATASET_LINK); 
            });
            // Initialize 'Insert workflow link' button.
            $('.galaxy_tools_insert_workflow_link').children().click( function() {
                editor.dialog(Galaxy.DIALOG_WORKFLOW_LINK); 
            });
            // Initialize 'Insert page link' button.
            $('.galaxy_tools_insert_page_link').children().click( function() {
                editor.dialog(Galaxy.DIALOG_PAGE_LINK); 
            });
            // Initialize 'Annotate history' button.
            $('.galaxy_tools_annotate_history').children().click( function() {
                editor.dialog(Galaxy.DIALOG_ANNOTATE_HISTORY); 
            });
            // Initialize galaxy elements.
            //init_galaxy_elts(editor);
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "base", "history", "autocomplete_tagging" )}
</%def>

<%def name="center_panel()">

    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner" style="float: right">
            <a id="save-button" class="panel-header-button">Save</a>
            <a id="close-button" class="panel-header-button">Close</a>
        </div>
        <div class="unified-panel-header-inner">
            Page Editor <span style="font-weight: normal">| Title : ${page.title}</span>
        </div>
    </div>

    <div class="unified-panel-body">
        <textarea name="page_content">${page.latest_revision.content.decode('utf-8')}</textarea>
    </div>

</%def>
