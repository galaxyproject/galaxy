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
            %if tool.name:
                <a id="link-${tool.id}" href="${link}" target=${tool.target} minsizehint="${tool.uihints.get( 'minwidth', -1 )}">${tool.name}</a> ${tool.description} 
            %else:
                <a id="link-${tool.id}" href="${link}" target=${tool.target} minsizehint="${tool.uihints.get( 'minwidth', -1 )}">${tool.description}</a>
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
        <a id="link-${workflow.id}" href="${ h.url_for( controller='workflow', action='run', id=encoded_id, check_user=False )}" target="_parent"}">${workflow.name}</a>
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
        <title>Galaxy Tools</title>
        <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
        <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
        <link href="${h.url_for('/static/style/tool_menu.css')}" rel="stylesheet" type="text/css" />

        <script type="text/javascript" src="${h.url_for('/static/scripts/jquery.js')}"></script>

        <script type="text/javascript">
            var q = jQuery.noConflict();
            q(document).ready(function() { 
                q( "div.toolSectionBody" ).hide();
                q( "div.toolSectionTitle > span" ).wrap( "<a href='#'></a>" )
                var last_expanded = null;
                q( "div.toolSectionTitle" ).each( function() { 
                   var body = q(this).next( "div.toolSectionBody" );
                   q(this).click( function() {
                       if ( body.is( ":hidden" ) ) {
                           if ( last_expanded ) last_expanded.slideUp( "fast" );
                           last_expanded = body;
                           body.slideDown( "fast" );
                       }
                       else {
                           body.slideUp( "fast" );
                           last_expanded = null;
                       }
                       return false;
                   });
                });
                q( "a[@minsizehint]" ).click( function() {
                    if ( parent.handle_minwidth_hint ) {
                        parent.handle_minwidth_hint( q(this).attr( "minsizehint" ) );
                    }
                });
            });
        </script>
    </head>

    <body class="toolMenuPage">
        <div class="toolMenu">
            <div class="toolSectionList">
                %for key, val in toolbox.tool_panel.items():
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
                %endfor
            </div>
        </div>
    </body>
</html>


