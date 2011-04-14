<%!
    import re
%>

<%namespace file="/tagging_common.mako" import="render_tool_tagging_elements" />

## Render a tool
<%def name="render_tool( tool, section )">
    %if not tool.hidden:
        %if section:
            <div class="toolTitle">
        %else:
            <div class="toolTitleNoSection">
        %endif
            <%
                if tool.input_required:
                    link = h.url_for( controller='tool_runner', tool_id=tool.id )
                else:
                    link = h.url_for( tool.action, ** tool.get_static_param_values( t ) )
            %>
            ## FIXME: This doesn't look right
            ## %if "[[" in tool.description and "]]" in tool.description:
            ##   ${tool.description.replace( '[[', '<a href="link" target="galaxy_main">' % $tool.id ).replace( "]]", "</a>" )
            <% tool_id = re.sub( '[^a-z0-9_]', '_', tool.id.lower() ) %>
            %if tool.name:
                <a class="link-${tool_id} tool-link" href="${link}" target=${tool.target} minsizehint="${tool.uihints.get( 'minwidth', -1 )}">${_(tool.name)}</a> ${tool.description} 
            %else:
                <a class="link-${tool_id} tool-link" href="${link}" target=${tool.target} minsizehint="${tool.uihints.get( 'minwidth', -1 )}">${tool.description}</a>
            %endif
        </div>
    %endif
</%def>

## Render a workflow
<%def name="render_workflow( key, workflow, section )">
    %if section:
        <div class="toolTitle">
    %else:
        <div class="toolTitleNoSection">
    %endif
        <% encoded_id = key.lstrip( 'workflow_' ) %>
        <a id="link-${workflow.id}" href="${ h.url_for( controller='workflow', action='run', id=encoded_id )}" target="_parent">${_(workflow.name)}</a>
    </div>
</%def>

## Render a label
<%def name="render_label( label )">
    <div class="toolPanelLabel" id="title_${label.id}">
        <span>${label.text}</span>
    </div>
</%def>

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
    <head>
        <title>${_('Galaxy Tools')}</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
        <link href="${h.url_for('/static/style/tool_menu.css')}" rel="stylesheet" type="text/css" />
        <link href="${h.url_for('/static/style/autocomplete_tagging.css')}" rel="stylesheet" type="text/css" />

        ##<script type="text/javascript" src="${h.url_for('/static/scripts/jquery.js')}"></script>
        ${h.js( "jquery", "galaxy.base", "json2", "autocomplete_tagging" )}

        <script type="text/javascript">
            // Set up GalaxyAsync object.
            var galaxy_async = new GalaxyAsync(${str(trans.app.config.log_actions).lower()});
            galaxy_async.set_func_url(galaxy_async.log_user_action, "${h.url_for( controller='user', action='log_user_action_async' )}");
        
            $(document).ready(function() { 
                // Init showing/hiding of tool sections.
                $( "div.toolSectionBody" ).hide();
                $( "div.toolSectionTitle > span" ).wrap( "<a href='#'></a>" )
                var last_expanded = null;
                $( "div.toolSectionTitle" ).each( function() { 
                    var body = $(this).next( "div.toolSectionBody" );
                    $(this).click( function() {
                        if ( body.is( ":hidden" ) ) {
                            if ( last_expanded ) {
                                last_expanded.slideUp( "fast" );
                            }
                            last_expanded = body;
                            body.slideDown( "fast" );
                        } else {
                            body.slideUp( "fast" );
                            last_expanded = null;
                        }
                        return false;
                    });
                });
                
                // Log clicks on tools.
                $("div.toolTitle > a").click( function() {
                    var tool_title = $(this).attr('id').split("-")[1];
                    var section_title = $.trim( $(this).parents("div.toolSectionWrapper").find("div.toolSectionTitle").text() );
                    var search_active = $(this).parents("div.toolTitle").hasClass("search_match");
                    
                    // Log action.
                    galaxy_async.log_user_action("tool_menu_click." + tool_title, section_title, 
                                                    JSON.stringify({"search_active" : search_active}));
                });
                
                $( "a[minsizehint]" ).click( function() {
                    if ( parent.handle_minwidth_hint ) {
                        parent.handle_minwidth_hint( $(this).attr( "minsizehint" ) );
                    }
                });
                
                // Init searching.
                $("#tool-search-query").click( function () {
                    $(this).focus();
                    $(this).select();
                }).keyup( function () {
                    // Remove italics.
                    $(this).css("font-style", "normal");
                    
                    // Don't update if same value as last time
                    if ( this.value.length < 3 ) {
                        reset_tool_search(false);
                    } else if ( this.value !== this.lastValue ) {
                        // Add class to denote that searching is active.
                        $(this).addClass("search_active");
                        // input.addClass(config.loadingClass);
                        // Add '*' to facilitate partial matching.
                        var q = this.value + '*';
                        // Stop previous ajax-request
                        if (this.timer) {
                            clearTimeout(this.timer);
                        }
                        // Start a new ajax-request in X ms
                        $("#search-spinner").show();
                        this.timer = setTimeout(function () {
                            $.get("${h.url_for( controller='root', action='tool_search' )}", { query: q }, function (data) {
                                // input.removeClass(config.loadingClass);
                                // Show live-search if results and search-term aren't empty
                                $("#search-no-results").hide();
                                // Hide all tool sections.
                                $(".toolSectionWrapper").hide();
                                // This hides all tools but not workflows link (which is in a .toolTitle div).
                                $(".toolSectionWrapper").find(".toolTitle").hide();
                                if ( data.length !== 0 ) {
                                    // Map tool ids to element ids and join them.
                                    var s = $.map( data, function( n, i ) { return ".link-" + n.toLowerCase().replace(/[^a-z0-9_]/g,'_'); } ).join( ", " );

                                    // First pass to show matching tools and their parents.
                                    $(s).each( function() {
                                        // Add class to denote match.
                                        $(this).parent().addClass("search_match");
                                        if ($(this).parents("#recently_used_wrapper").length === 0) {
                                            // Default behavior.
                                            $(this).parent().show().parent().parent().show().parent().show();
                                        } else if ($(this).parents(".user_pref_visible").length !== 0) {
                                            // RU menu is visible, so filter it as normal.
                                            $(this).parent().show().parent().parent().show().parent().show();
                                        } else  {
                                            // RU menu is not visible, so set up classes and visibility so that if menu shown matching is 
                                            // aleady in place.
                                            $(this).parent().show();
                                        }
                                    });
                                    
                                    // Hide labels that have no visible children.
                                    $(".toolPanelLabel").each( function() {
                                        var this_label = $(this);                                   
                                        var next = this_label.next();
                                        var no_visible_tools = true;
                                        // Look through tools following label and, if none are visible, hide label.
                                        while (next.length !== 0 && next.hasClass("toolTitle")) {
                                            if (next.is(":visible")) {
                                                no_visible_tools = false;
                                                break;
                                            } else {
                                                next = next.next();
                                            }
                                        }
                                        if (no_visible_tools) {
                                            this_label.hide();
                                        }
                                    });
                                } else {
                                    $("#search-no-results").show();
                                }
                                $("#search-spinner").hide();
                            }, "json" );
                        }, 200 );
                    }
                    this.lastValue = this.value;
                });                
            });            

            // Update recently used tools menu. Function inserts a new item and removes the last item.
            function update_recently_used() {
                $.ajax({
                    url: "${h.url_for( controller='/user', action='get_most_recently_used_tool_async' )}",
                    dataType: 'json',
                    error: function() { 
                        // console.log( "Failed to update recently used list." );
                    },
                    success: function(new_tool_info) {
                        var recently_used_elts = $("#recently_used").find(".toolTitle");
                        var first_elt = $(recently_used_elts.first());
                        var found_in_list = false;
            
                        // Look for new tool in current list. If found, rearrange list to move tool to top.
                        var new_tool_info_id = new_tool_info.id.toLowerCase().replace(/[^a-z0-9_]/, "_")
                        recently_used_elts.each( function(index) {
                            var anchor = $(this).find("a");
                            if (anchor.hasClass("link-" + new_tool_info_id)) {
                                found_in_list = true;
                    
                                // If tool is first, do nothing.
                                if (index === 0) {
                                    return;
                                } else {
                                    // Tool not first; reorder.
                                    $(this).remove();
                                    first_elt.before($(this));
                                }
                            }
                        });
            
                        // If tool not in list, create new element, remove last element, and put new element first in list.
                        if (!found_in_list) {
                            new_tool_elt = $("<div class='toolTitle'> \
                                                <a class='link-" + new_tool_info.id + "' href='" + new_tool_info.link + "' target='" + 
                                                new_tool_info.target + "' minsizehint='" + new_tool_info.minsizehint + "'>" +
                                                new_tool_info.name + "</a> " + new_tool_info.description + " \
                                              </div>");
                            recently_used_elts.last().remove();
                            recently_used_elts.first().before(new_tool_elt);                            
                        }
                    }
                });                

            }

            var current_tags = new Array();
            function tool_tag_click(tag_name, tag_value) {
                var add = true;
                for ( var i = 0 ; i < current_tags.length ; i++ ) {
                    if ( current_tags[i] == tag_name ) {
                        current_tags.splice( i, 1 );
                        add = false;
                    }
                }
                if ( add ) {
                    current_tags.push( tag_name );
                    $("span.tag-name").each( function() {
                        if ( $(this).text() == tag_name ) {
                            $(this).addClass("active-tag-name");
                            $(this).append("<img class='delete-tag-img' src='${h.url_for('/static/images/delete_tag_icon_gray.png')}'/>")
                        }
                    });
                } else {
                    $("span.tag-name").each( function() {
                        if ( $(this).text() == tag_name ) {
                            $(this).removeClass("active-tag-name");
                            $(this).text(tag_name);
                        }
                    });
                }
                if ( current_tags.length == 0 ) {
                    $("#search-no-results").hide();
                    $(".tool-link").each( function() {
                        $(this).parent().removeClass("search_match");
                        if ($(this).parents("#recently_used_wrapper").length === 0) {
                            // Default behavior.
                            $(this).parent().show().parent().parent().hide().parent().show();
                        } else if ($(this).parents(".user_pref_visible").length !== 0) {
                            // RU menu is visible, so filter it as normal.
                            $(this).parent().show().parent().parent().show().parent().show();
                        } else  {
                            // RU menu is not visible, so set up classes and visibility so that if menu shown matching is 
                            // aleady in place.
                            $(this).parent().show();
                        }
                    });
                    return;
                }
                $.get("${h.url_for( controller='root', action='tool_tag_search' )}", { query: current_tags }, function (data) {
                    // Show live-search if results and search-term aren't empty
                    $("#search-no-results").hide();
                    // Hide all tool sections.
                    $(".toolSectionWrapper").hide();
                    // This hides all tools but not workflows link (which is in a .toolTitle div).
                    $(".toolSectionWrapper").find(".toolTitle").hide();
                    if ( data.length !== 0 ) {
                        // Map tool ids to element ids and join them.
                        var s = $.map( data, function( n, i ) { return ".link-" + n.toLowerCase().replace(/[^a-z0-9_]/g,'_'); } ).join( ", " );

                        // First pass to show matching tools and their parents.
                        $(s).each( function() {
                            // Add class to denote match.
                            $(this).parent().addClass("search_match");
                            if ($(this).parents("#recently_used_wrapper").length === 0) {
                                // Default behavior.
                                $(this).parent().show().parent().parent().show().parent().show();
                            } else if ($(this).parents(".user_pref_visible").length !== 0) {
                                // RU menu is visible, so filter it as normal.
                                $(this).parent().show().parent().parent().show().parent().show();
                            } else  {
                                // RU menu is not visible, so set up classes and visibility so that if menu shown matching is 
                                // aleady in place.
                                $(this).parent().show();
                            }
                        });
                        
                        // Hide labels that have no visible children.
                        $(".toolPanelLabel").each( function() {
                            var this_label = $(this);                                   
                            var next = this_label.next();
                            var no_visible_tools = true;
                            // Look through tools following label and, if none are visible, hide label.
                            while (next.length !== 0 && next.hasClass("toolTitle")) {
                                if (next.is(":visible")) {
                                    no_visible_tools = false;
                                    break;
                                } else {
                                    next = next.next();
                                }
                            }
                            if (no_visible_tools) {
                                this_label.hide();
                            }
                        });
                    } else {
                        $("#search-no-results").show();
                    }
                }, "json" );
            }

        </script>
    </head>

    <body class="toolMenuPage">
        <div class="toolMenu">
            
                ## Tool search.
                <%
                    show_tool_search = False
                    if trans.user:
                        show_tool_search = trans.user.preferences.get( "show_tool_search", "False" )
                    
                    if show_tool_search == "True":
                        display = "block"
                    else:
                        display = "none"
                %>
                <div id="tool-search" style="padding-bottom: 5px; position: relative; display: ${display}; width: 100%">
                    %if trans.app.config.get_bool( 'enable_tool_tags', False ):
                        <b>Tags:</b>
                        ${render_tool_tagging_elements()}
                    %endif
                    <input type="text" name="query" value="search tools" id="tool-search-query" autocomplete="off" style="width: 100%; font-style:italic; font-size: inherit"/>
                    <img src="${h.url_for('/static/images/loading_small_white_bg.gif')}" id="search-spinner" style="display: none; position: absolute; right: 0; top: 5px;"/>
                </div>
                
                ## Recently used tools.
                %if trans.user:
                    <%
                    if trans.user.preferences.get( 'show_recently_used_menu', 'False' ) == 'True':
                        display = "block"
                        pref_class = "user_pref_visible"
                    else:
                        display = "none"
                        pref_class = "user_pref_hidden"
                    %>
                    <div class="toolSectionWrapper ${pref_class}" id="recently_used_wrapper" 
                            style="display: ${display}; padding-bottom: 5px">
                        <div class="toolSectionTitle">
                            <span>Recently Used</span>
                        </div>
                        <div id="recently_used" class="toolSectionBody">
                            <div class="toolSectionBg">
                                %for tool in recent_tools:
                                    ${render_tool( tool, True )}
                                %endfor
                            </div>
                        </div>
                        <div class="toolSectionPad"></div>
                    </div>
                %endif
                
                ## Tools.
                %for key, val in toolbox.tool_panel.items():
                    <div class="toolSectionWrapper">
                    %if key.startswith( 'tool' ):
                        ${render_tool( val, False )}
                    %elif key.startswith( 'workflow' ):
                        ${render_workflow( key, val, False )}
                    %elif key.startswith( 'section' ):
                        <% section = val %>
                        <div class="toolSectionTitle" id="title_${section.id}">
                            <span>${section.name}</span>
                        </div>
                        <div id="${section.id}" class="toolSectionBody">
                            <div class="toolSectionBg">
                                %for section_key, section_val in section.elems.items():
                                    %if section_key.startswith( 'tool' ):
                                        ${render_tool( section_val, True )}
                                    %elif section_key.startswith( 'workflow' ):
                                        ${render_workflow( section_key, section_val, True )}
                                    %elif section_key.startswith( 'label' ):
                                        ${render_label( section_val )}
                                    %endif
                                %endfor
                            </div>
                        </div>
                    %elif key.startswith( 'label' ):
                        ${render_label( val )}
                    %endif
                    <div class="toolSectionPad"></div>
                    </div>
                %endfor
                
                ## Feedback when search returns no results.
                <div id="search-no-results" style="display: none; padding-top: 5px">
                    <em><strong>Search did not match any tools.</strong></em>
                </div>
                
                ## Link to workflow management. The location of this may change, but eventually
                ## at least some workflows will appear here (the user should be able to
                ## configure which of their stored workflows appear in the tools menu). 
                
                %if t.user:
                    <div class="toolSectionPad"></div>
                    <div class="toolSectionPad"></div>
                    <div class="toolSectionTitle" id="title_XXinternalXXworkflow">
                      <span>Workflows</span>
                    </div>
                    <div id="XXinternalXXworkflow" class="toolSectionBody">
                        <div class="toolSectionBg">
                            %if t.user.stored_workflow_menu_entries:
                                %for m in t.user.stored_workflow_menu_entries:
                                    <div class="toolTitle">
                                        <a href="${h.url_for( controller='workflow', action='run', id=trans.security.encode_id(m.stored_workflow_id) )}" target="galaxy_main">${m.stored_workflow.name}</a>
                                    </div>
                                %endfor
                            %endif
                            <div class="toolTitle">
                                <a href="${h.url_for( controller='workflow', action='list_for_run')}" target="galaxy_main">All workflows</a>
                            </div>
                        </div>
                    </div>
                %endif
                
            </div>
        </div>
    </body>
</html>
