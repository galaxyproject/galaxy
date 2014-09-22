// Useful Galaxy stuff.
var Galaxy = 
{
    // Item types.
    ITEM_HISTORY : "item_history",
    ITEM_DATASET : "item_dataset",
    ITEM_WORKFLOW : "item_workflow",
    ITEM_PAGE : "item_page",
    ITEM_VISUALIZATION : "item_visualization",
    
    // Link dialogs.
    DIALOG_HISTORY_LINK : "link_history",
    DIALOG_DATASET_LINK : "link_dataset",
    DIALOG_WORKFLOW_LINK : "link_workflow",
    DIALOG_PAGE_LINK : "link_page",
    DIALOG_VISUALIZATION_LINK : "link_visualization",
    
    // Embed dialogs.
    DIALOG_EMBED_HISTORY : "embed_history",
    DIALOG_EMBED_DATASET : "embed_dataset",
    DIALOG_EMBED_WORKFLOW : "embed_workflow",
    DIALOG_EMBED_PAGE : "embed_page",
    DIALOG_EMBED_VISUALIZATION : "embed_visualization"
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

// Based on the dialog type, return a dictionary of information about an item
function get_item_info( dialog_type )
{
    var
        item_singular, 
        item_plural, 
        item_controller;
    switch( dialog_type ) {
        case( Galaxy.ITEM_HISTORY ):
            item_singular = "History";
            item_plural = "Histories";
            item_controller = "history";
            item_class = "History";
            break;
        case( Galaxy.ITEM_DATASET ):
            item_singular = "Dataset";
            item_plural = "Datasets";
            item_controller = "dataset";
            item_class = "HistoryDatasetAssociation";
            break;
        case( Galaxy.ITEM_WORKFLOW ):
            item_singular = "Workflow";
            item_plural = "Workflows";
            item_controller = "workflow";
            item_class = "StoredWorkflow";
            break;
        case( Galaxy.ITEM_PAGE ):
            item_singular = "Page";
            item_plural = "Pages";
            item_controller = "page";
            item_class = "Page";
            break;
        case( Galaxy.ITEM_VISUALIZATION ):
            item_singular = "Visualization";
            item_plural = "Visualizations";
            item_controller = "visualization";
            item_class = "Visualization";
            break;
    }
    
    // Build ajax URL that lists items for selection.
    var item_list_action = "list_" + item_plural.toLowerCase() + "_for_selection";
    var ajax_url = list_objects_url.replace( "LIST_ACTION", item_list_action );
    
    // Set up and return dict.
    return {
        singular : item_singular,
        plural : item_plural,
        controller : item_controller,
        iclass : item_class,
        list_ajax_url : ajax_url
    };
};

// Make an item importable.
function make_item_importable( item_controller, item_id, item_type )
{
    ajax_url = set_accessible_url.replace( "ITEM_CONTROLLER", item_controller );
    $.ajax({
      type: "POST",
      url: ajax_url,
      data: { id: item_id, accessible: 'True' },
      error: function() { alert("Making " + item_type + " accessible failed"); }
    });
};

// Completely replace WYM's dialog handling
WYMeditor.editor.prototype.dialog = function( dialogType, dialogFeatures, bodyHtml ) {
      
    var wym = this;
    var sStamp = wym.uniqueStamp();
    var selected = wym.selected();
    
    // Swap out URL attribute for id/name attribute in link creation to enable anchor creation in page.
    function set_link_id() 
    {
        // When "set link id" link clicked, update UI.
        $('#set_link_id').click( function() 
        {
            // Set label.
            $("#link_attribute_label").text("ID/Name");
            
            // Set input elt class, value.
            var attribute_input = $(".wym_href");
            attribute_input.addClass("wym_id").removeClass("wym_href");
            if (selected)
                attribute_input.val( $(selected).attr('id') );
            
            // Remove link.
            $(this).remove();
        });
    }
    
    // LINK DIALOG
    if ( dialogType == WYMeditor.DIALOG_LINK ) {
        if(selected) {
            $(wym._options.hrefSelector).val($(selected).attr(WYMeditor.HREF));
            $(wym._options.srcSelector).val($(selected).attr(WYMeditor.SRC));
            $(wym._options.titleSelector).val($(selected).attr(WYMeditor.TITLE));
            $(wym._options.altSelector).val($(selected).attr(WYMeditor.ALT));
        }
        // Get current URL, title.
        var curURL, curTitle;
        if (selected)
        {
            curURL = $(selected).attr("href");
            if (curURL == undefined)
                curURL = "";
            curTitle = $(selected).attr("title");
            if (curTitle == undefined)
                curTitle = "";
        }
        show_modal(
            "Create Link",
            "<div><div><label id='link_attribute_label'>URL <span style='float: right; font-size: 90%'><a href='#' id='set_link_id'>Create in-page anchor</a></span></label><br><input type='text' class='wym_href' value='" + curURL + "' size='40' /></div>"
                + "<div><label>Title</label><br><input type='text' class='wym_title' value='" + curTitle + "' size='40' /></div><div>",
            {
                "Make link": function() {
                    // Get URL, name/title.
                    var sUrl = $(wym._options.hrefSelector).val() || '',
                        sId = $(".wym_id").val() || '',
                        sName = $(wym._options.titleSelector).val() || '';
                    
                    if (sUrl || sId) {
                        // Create link.
                        wym._exec(WYMeditor.CREATE_LINK, sStamp);
                        
                        // Set link attributes.
                        var link = $("a[href=" + sStamp + "]", wym._doc.body);
                        link.attr(WYMeditor.HREF, sUrl)
                            .attr(WYMeditor.TITLE, sName)
                            .attr("id", sId);

                        // If link's text is default (wym-...), change it to the title.
                        if (link.text().indexOf('wym-') === 0) {
                            link.text(sName);
                        }
                    }
                    hide_modal();
                },
                "Cancel": function() {
                    hide_modal();
                }
            },
            {},
            set_link_id
        );
    }
    
    // IMAGE DIALOG
    if ( dialogType == WYMeditor.DIALOG_IMAGE ) {
        if(wym._selected_image) {
            $(wym._options.dialogImageSelector + " " + wym._options.srcSelector)
              .val($(wym._selected_image).attr(WYMeditor.SRC));
            $(wym._options.dialogImageSelector + " " + wym._options.titleSelector)
              .val($(wym._selected_image).attr(WYMeditor.TITLE));
            $(wym._options.dialogImageSelector + " " + wym._options.altSelector)
              .val($(wym._selected_image).attr(WYMeditor.ALT));
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
                    var sUrl = $(wym._options.srcSelector).val();
                    if(sUrl.length > 0) {
                      wym._exec(WYMeditor.INSERT_IMAGE, sStamp);
                      $("img[src$=" + sStamp + "]", wym._doc.body)
                          .attr(WYMeditor.SRC, sUrl)
                          .attr(WYMeditor.TITLE, $(wym._options.titleSelector).val())
                          .attr(WYMeditor.ALT, $(wym._options.altSelector).val());
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
                    var iRows = $(wym._options.rowsSelector).val();
                    var iCols = $(wym._options.colsSelector).val();
              
                    if(iRows > 0 && iCols > 0) {
              
                      var table = wym._doc.createElement(WYMeditor.TABLE);
                      var newRow = null;
                              var newCol = null;
              
                              var sCaption = $(wym._options.captionSelector).val();
              
                              //we create the caption
                              var newCaption = table.createCaption();
                              newCaption.innerHTML = sCaption;
              
                              //we create the rows and cells
                              for(x=0; x<iRows; x++) {
                                      newRow = table.insertRow(x);
                                      for(y=0; y<iCols; y++) {newRow.insertCell(y);}
                              }
              
                      //set the summary attr
                      $(table).attr('summary',
                          $(wym._options.summarySelector).val());
              
                      //append the table after the selected container
                      var node = $(wym.findUp(wym.container(),
                        WYMeditor.MAIN_CONTAINERS)).get(0);
                      if(!node || !node.parentNode) $(wym._doc.body).append(table);
                      else $(node).after(table);
                    }
                    hide_modal();
                },
                "Cancel": function() {
                    hide_modal();
                }
            }
        );
    }
    
    // INSERT "GALAXY ITEM" LINK DIALOG
    if ( dialogType == Galaxy.DIALOG_HISTORY_LINK || dialogType == Galaxy.DIALOG_DATASET_LINK || 
         dialogType == Galaxy.DIALOG_WORKFLOW_LINK || dialogType == Galaxy.DIALOG_PAGE_LINK || 
         dialogType == Galaxy.DIALOG_VISUALIZATION_LINK ) {
        // Based on item type, set useful vars.
        var item_info;
        switch(dialogType)
        {
            case(Galaxy.DIALOG_HISTORY_LINK):
                item_info = get_item_info(Galaxy.ITEM_HISTORY);
                break;
            case(Galaxy.DIALOG_DATASET_LINK):
                item_info = get_item_info(Galaxy.ITEM_DATASET);
                break;
            case(Galaxy.DIALOG_WORKFLOW_LINK):
                item_info = get_item_info(Galaxy.ITEM_WORKFLOW);
                break;
            case(Galaxy.DIALOG_PAGE_LINK):
                item_info = get_item_info(Galaxy.ITEM_PAGE);
                break;
            case(Galaxy.DIALOG_VISUALIZATION_LINK):
                item_info = get_item_info(Galaxy.ITEM_VISUALIZATION);
                break;
        }
        
        $.ajax(
        {
            url: item_info.list_ajax_url,
            data: {},
            error: function() { alert( "Failed to list "  + item_info.plural.toLowerCase() + " for selection"); },
            success: function(table_html) 
            {
                show_modal(
                    "Insert Link to " + item_info.singular,
                    table_html +
                    "<div><input id='make-importable' type='checkbox' checked/>" +
                    "Make the selected " + item_info.plural.toLowerCase() + " accessible so that they can viewed by everyone.</div>"
                    ,
                    {
                        "Insert": function() 
                        {
                            // Make selected items accessible (importable) ?
                            var make_importable = false;
                            if ( $('#make-importable:checked').val() !== null )
                                make_importable = true;
                            
                            // Insert links to history for each checked item.
                            var item_ids = new Array();
                            $('input[name=id]:checked').each(function() {
                                var item_id = $(this).val();
                                
                                // Make item importable?
                                if (make_importable)
                                    make_item_importable(item_info.controller, item_id, item_info.singular);
                                
                                // Insert link(s) to item(s). This is done by getting item info and then manipulating wym.
                                url_template = get_name_and_link_url + item_id;
                                ajax_url = url_template.replace( "ITEM_CONTROLLER", item_info.controller);
                                $.getJSON( ajax_url, function( returned_item_info ) {
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
                                        wym.insert("<a href='" + returned_item_info.link + "'>" + item_info.singular + " '" + returned_item_info.name + "'</a>");
                                    }
                                    else
                                    {
                                        // Link created from selected text; add href and title.
                                        $("a[href=" + sStamp + "]", wym._doc.body).attr(WYMeditor.HREF, returned_item_info.link).attr(WYMeditor.TITLE, item_info.singular + item_id);
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
    // EMBED GALAXY OBJECT DIALOGS
    if ( dialogType == Galaxy.DIALOG_EMBED_HISTORY || dialogType == Galaxy.DIALOG_EMBED_DATASET || dialogType == Galaxy.DIALOG_EMBED_WORKFLOW || dialogType == Galaxy.DIALOG_EMBED_PAGE || dialogType == Galaxy.DIALOG_EMBED_VISUALIZATION ) {
        // Based on item type, set useful vars.
        var item_info;
        switch(dialogType)
        {
            case(Galaxy.DIALOG_EMBED_HISTORY):
                item_info = get_item_info(Galaxy.ITEM_HISTORY);
                break;
            case(Galaxy.DIALOG_EMBED_DATASET):
                item_info = get_item_info(Galaxy.ITEM_DATASET);
                break;
            case(Galaxy.DIALOG_EMBED_WORKFLOW):
                item_info = get_item_info(Galaxy.ITEM_WORKFLOW);
                break;
            case(Galaxy.DIALOG_EMBED_PAGE):
                item_info = get_item_info(Galaxy.ITEM_PAGE);
                break;
            case(Galaxy.DIALOG_EMBED_VISUALIZATION):
                item_info = get_item_info(Galaxy.ITEM_VISUALIZATION);
                break;
        }
        
        $.ajax(
        {
            url: item_info.list_ajax_url,
            data: {},
            error: function() { alert( "Failed to list "  + item_info.plural.toLowerCase() + " for selection"); },
            success: function(list_html) 
            {
                // Can make histories, workflows importable; cannot make datasets importable.
                if (dialogType == Galaxy.DIALOG_EMBED_HISTORY || dialogType == Galaxy.DIALOG_EMBED_WORKFLOW 
                    || dialogType == Galaxy.DIALOG_EMBED_VISUALIZATION)
                    list_html = list_html + "<div><input id='make-importable' type='checkbox' checked/>" +
                                "Make the selected " + item_info.plural.toLowerCase() + " accessible so that they can viewed by everyone.</div>";
                show_modal(
                    "Embed " + item_info.plural,
                    list_html,
                    {
                        "Embed": function() 
                        {   
                            // Make selected items accessible (importable) ?
                            var make_importable = false;
                            if ( $('#make-importable:checked').val() != null )
                                make_importable = true;
                            
                            $('input[name=id]:checked').each(function() {
                                // Get item ID and name.
                                var item_id = $(this).val();
                                // Use ':first' because there are many labels in table; the first one is the item name.
                                var item_name = $("label[for='" + item_id + "']:first").text();
                                
                                if (make_importable)
                                    make_item_importable(item_info.controller, item_id, item_info.singular);
                                
                                // Embedded item HTML; item class is embedded in div container classes; this is necessary because the editor strips 
                                // all non-standard attributes when it returns its content (e.g. it will not return an element attribute of the form 
                                // item_class='History').
                                var item_elt_id = item_info.iclass + "-"  + item_id;
                                var item_embed_html = [
                                    "<div id='", item_elt_id, "' class='embedded-item ",
                                            item_info.singular.toLowerCase(), " placeholder'>",
                                        "<p class='title'>",
                                            "Embedded Galaxy ", item_info.singular, " '", item_name, "'",
                                        "</p>",
                                        "<p class='content'>",
                                            "[Do not edit this block; Galaxy will fill it in with the annotated ",
                                            item_info.singular.toLowerCase(), " when it is displayed.]",
                                        "</p>",
                                    "</div>" ].join( '' );
                                
                                // Insert embedded item into document.
                                wym.insert(item_embed_html);
                                
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

$(function(){
    // Generic error handling
    $(document).ajaxError( function ( e, x ) {
        // console.log( e, x );
        var message = x.responseText || x.statusText || "Could not connect to server";
        show_modal( "Server error", message, { "Ignore error" : hide_modal } );
        return false;
    });
    // Create editor
    $("[name=page_content]").wymeditor( {
        skin: 'galaxy',
        basePath: editor_base_path,
        iframeBasePath: iframe_base_path,
        boxHtml:   "<table class='wym_box' width='100%' height='100%'>"
                    + "<tr><td><div class='wym_area_top'>" 
                    + WYMeditor.TOOLS
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
    // Get the editor object
    var editor = $.wymeditors(0);
    var save = function ( callback ) {
        show_modal( "Saving page", "progress" );
        
        // Do save.
        $.ajax( {
            url: save_url,
            type: "POST",
            data: {
                id: page_id,
                content: editor.xhtml(),
                annotations: JSON.stringify(new Object()), 
                // annotations: JSON.stringify(annotations),
                "_": "true"
            },
            success: function() {
                callback();
            }
        });
    }
    // Save button
    $("#save-button").click( function() {
        save( function() { hide_modal(); } )
    });
    // Close button
    $("#close-button").click(function() {
        // var new_content = editor.xhtml();
        // var changed = ( initial_content != new_content );
        var changed = false;
        if ( changed ) {
            var do_close = function() {
                window.onbeforeunload = undefined;
                window.document.location = page_list_url;
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
            window.document.location = page_list_url;
        }
    });
    
    // Initialize galaxy elements.
    //init_galaxy_elts(editor);
    
    //
    // Containers, Galaxy style
    //
    var containers_menu = $("<div class='galaxy-page-editor-button'><a id='insert-galaxy-link' class='action-button popup' href='#'>Paragraph type</a></div>");
    $(".wym_area_top").append( containers_menu );
                
    // Add menu options.
    var items = {}
    $.each( editor._options.containersItems, function( k, v ) {
        var tagname = v.name;
        items[ v.title.replace( '_', ' ' ) ] = function() { editor.container( tagname ) }
    });
    make_popupmenu( containers_menu, items);
    
    //
    // Create 'Insert Link to Galaxy Object' menu.
    //
    
    // Add menu button.
    var insert_link_menu_button = $("<div><a id='insert-galaxy-link' class='action-button popup' href='#'>Insert Link to Galaxy Object</a></div>").addClass('galaxy-page-editor-button');
    $(".wym_area_top").append(insert_link_menu_button);
    
    // Add menu options.
    make_popupmenu( insert_link_menu_button, {
        "Insert History Link": function() {
            editor.dialog(Galaxy.DIALOG_HISTORY_LINK);
        },
        "Insert Dataset Link": function() {
            editor.dialog(Galaxy.DIALOG_DATASET_LINK);
        },
        "Insert Workflow Link": function() {
            editor.dialog(Galaxy.DIALOG_WORKFLOW_LINK);
        },
        "Insert Page Link": function() {
            editor.dialog(Galaxy.DIALOG_PAGE_LINK);
        },
        "Insert Visualization Link": function() {
            editor.dialog(Galaxy.DIALOG_VISUALIZATION_LINK);
        },
    });
    
    //
    // Create 'Embed Galaxy Object' menu.
    //
    
    // Add menu button.
    var embed_object_button = $("<div><a id='embed-galaxy-object' class='action-button popup' href='#'>Embed Galaxy Object</a></div>").addClass('galaxy-page-editor-button');
    $(".wym_area_top").append(embed_object_button);
    
    // Add menu options.
    make_popupmenu( embed_object_button, {
        "Embed History": function() {
            editor.dialog(Galaxy.DIALOG_EMBED_HISTORY);
        },
        "Embed Dataset": function() {
            editor.dialog(Galaxy.DIALOG_EMBED_DATASET);
        },
        "Embed Workflow": function() {
            editor.dialog(Galaxy.DIALOG_EMBED_WORKFLOW);
        },
        "Embed Visualization": function() {
            editor.dialog(Galaxy.DIALOG_EMBED_VISUALIZATION);
        },
        //"Embed Page": function() {
        //    editor.dialog(Galaxy.DIALOG_EMBED_PAGE);
        //}
    });                   
});
