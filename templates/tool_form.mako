<!-- -->
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">

<%
from galaxy.util.expressions import ExpressionContext 
%>

<html>

<head>
<title>Galaxy</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
<script type='text/javascript' src="${h.url_for('/static/scripts/jquery.js')}"> </script>
<script type="text/javascript">
$( function() {
    $( "select[refresh_on_change='true']").change( function() {
        var refresh = false;
        var refresh_on_change_values = $( this )[0].attributes.getNamedItem( 'refresh_on_change_values' )
        if ( refresh_on_change_values ) {
            refresh_on_change_values = refresh_on_change_values.value.split( ',' );
            var last_selected_value = $( this )[0].attributes.getNamedItem( 'last_selected_value' );
            for( i= 0; i < refresh_on_change_values.length; i++ ) {
                if ( $( this )[0].value == refresh_on_change_values[i] || ( last_selected_value && last_selected_value.value == refresh_on_change_values[i] ) ){
                    refresh = true;
                    break;
                }
            }
        }
        else {
            refresh = true;
        }
        if ( refresh ){
            $( ':file' ).each( function() {
                var file_value = $( this )[0].value;
                if ( file_value ) {
                    //disable file input, since we don't want to upload the file on refresh
                    var file_name = $( this )[0].name;
                    $( this )[0].name = 'replaced_file_input_' + file_name
                    $( this )[0].disable = true;
                    //create a new hidden field which stores the filename and has the original name of the file input
                    var new_file_input = document.createElement( 'input' );
                    new_file_input.type = 'hidden';
                    new_file_input.value = file_value;
                    new_file_input.name = file_name;
                    document.getElementById( 'tool_form' ).appendChild( new_file_input );
                }
            } );
            $( "#tool_form" ).submit();
        }
    });
});
%if not add_frame.debug:
    if( window.name != "galaxy_main" ) {
        location.replace( '${h.url_for( controller='root', action='index', tool_id=tool.id )}' );
    }
%endif
function checkUncheckAll( name, check )
{
    if ( check == 0 )
    {
        $("input[name=" + name + "][type='checkbox']").attr('checked', false);
    }
    else
    {
        $("input[name=" + name + "][type='checkbox']").attr('checked', true );
    }
}

</script>
</head>

<body>
    <%def name="do_inputs( inputs, tool_state, errors, prefix, other_values=None )">
      <% other_values = ExpressionContext( tool_state, other_values ) %>
        %for input_index, input in enumerate( inputs.itervalues() ):
            %if input.type == "repeat":
              <div class="repeat-group">
                  <div class="form-title-row"><b>${input.title_plural}</b></div>
                  <% repeat_state = tool_state[input.name] %>
                  %for i in range( len( repeat_state ) ):
                    <div class="repeat-group-item">
                    <%
                    if input.name in errors:
                        rep_errors = errors[input.name][i]
                    else:
                        rep_errors = dict()
                    index = repeat_state[i]['__index__']
                    %>
                    <div class="form-title-row"><b>${input.title} ${i + 1}</b></div>
                    ${do_inputs( input.inputs, repeat_state[i], rep_errors, prefix + input.name + "_" + str(index) + "|", other_values )}
                    <div class="form-row"><input type="submit" name="${prefix}${input.name}_${index}_remove" value="Remove ${input.title} ${i+1}"></div>
                    </div>
                  %endfor
                  <div class="form-row"><input type="submit" name="${prefix}${input.name}_add" value="Add new ${input.title}"></div>
              </div>
            %elif input.type == "conditional":
                <%
                group_state = tool_state[input.name]
                group_errors = errors.get( input.name, {} )
                current_case = group_state['__current_case__']
                group_prefix = prefix + input.name + "|"
                %>
                %if input.value_ref_in_group:
                    ${row_for_param( group_prefix, input.test_param, group_state, group_errors, other_values )}
                %endif
                ${do_inputs( input.cases[current_case].inputs, group_state, group_errors, group_prefix, other_values )}
            %elif input.type == "upload_dataset":
                %if input.get_datatype( trans, other_values ).composite_type is None: #have non-composite upload appear as before
                    <%
                    if input.name in errors:
                        rep_errors = errors[input.name][0]
                    else:
                        rep_errors = dict()
                    %>
                  ${do_inputs( input.inputs, tool_state[input.name][0], rep_errors, prefix + input.name + "_" + str( 0 ) + "|", other_values )}
                %else:
                    <div class="repeat-group">
                        <div class="form-title-row"><b>${input.group_title( other_values )}</b></div>
                        <% 
                        repeat_state = tool_state[input.name] 
                        %>
                        %for i in range( len( repeat_state ) ):
                          <div class="repeat-group-item">
                          <%
                          if input.name in errors:
                              rep_errors = errors[input.name][i]
                          else:
                              rep_errors = dict()
                          index = repeat_state[i]['__index__']
                          %>
                          <div class="form-title-row"><b>File Contents for ${input.title_by_index( trans, i, other_values )}</b></div>
                          ${do_inputs( input.inputs, repeat_state[i], rep_errors, prefix + input.name + "_" + str(index) + "|", other_values )}
                          ##<div class="form-row"><input type="submit" name="${prefix}${input.name}_${index}_remove" value="Remove ${input.title} ${i+1}"></div>
                          </div>
                        %endfor
                        ##<div class="form-row"><input type="submit" name="${prefix}${input.name}_add" value="Add new ${input.title}"></div>
                    </div>
                %endif
            %else:
                ${row_for_param( prefix, input, tool_state, errors, other_values )}
            %endif
        %endfor  
    </%def>
    
    <%def name="row_for_param( prefix, param, parent_state, parent_errors, other_values )">
        <%
        if parent_errors.has_key( param.name ):
            cls = "form-row form-row-error"
        else:
            cls = "form-row"
        %>
        <div class="${cls}">
            <% label = param.get_label() %>
            %if label:
                <label>
                    ${label}:
                </label>
            %endif
            <%
            field = param.get_html_field( trans, parent_state[ param.name ], other_values )
            field.refresh_on_change = param.refresh_on_change
            %>
            <div class="form-row-input">${field.get_html( prefix )}</div>
            %if parent_errors.has_key( param.name ):
            <div class="form-row-error-message">
                <div><img style="vertical-align: middle;" src="${h.url_for('/static/style/error_small.png')}">&nbsp;<span style="vertical-align: middle;">${parent_errors[param.name]}</span></div>
            </div>
            %endif
            
            %if param.help:
            <div class="toolParamHelp" style="clear: both;">
                ${param.help}
            </div>
            %endif
    
            <div style="clear: both"></div>
                    
        </div>
    </%def>
    
    %if add_frame.from_noframe:
        <div class="warningmessage">
        <strong>Welcome to Galaxy</strong>
        <hr/>
        It appears that you found this tool from a link outside of Galaxy.
        If you're not familiar with Galaxy, please consider visiting the
        <a href="${h.url_for( controller='root' )}" target="_top">welcome page</a>.
        To learn more about what Galaxy is and what it can do for you, please visit
        the <a href="$add_frame.wiki_url" target="_top">Galaxy wiki</a>.
        </div>
        <br/>
    %endif
    
    <div class="toolForm" id="${tool.id}">
        %if tool.has_multiple_pages:
            <div class="toolFormTitle">${tool.name} (step ${tool_state.page+1} of ${tool.npages})</div>
        %else:
            <div class="toolFormTitle">${tool.name}</div>
        %endif
        <div class="toolFormBody">
            <form id="tool_form" name="tool_form" action="${h.url_for( tool.action )}" enctype="${tool.enctype}" target="${tool.target}" method="${tool.method}">
                <input type="hidden" name="tool_id" value="${tool.id}">
                <input type="hidden" name="tool_state" value="${util.object_to_string( tool_state.encode( tool, app ) )}">
                %if tool.display_by_page[tool_state.page]:
                    ${trans.fill_template_string( tool.display_by_page[tool_state.page], context=tool.get_param_html_map( trans, tool_state.page, tool_state.inputs ) )}
                    <input type="submit" class="primary-button" name="runtool_btn" value="Execute">
                %else:
                    ${do_inputs( tool.inputs_by_page[ tool_state.page ], tool_state.inputs, errors, "" )}
                    <div class="form-row">
                        %if tool_state.page == tool.last_page:
                            <input type="submit" class="primary-button" name="runtool_btn" value="Execute">
                        %else:
                            <input type="submit" class="primary-button" name="runtool_btn" value="Next step">
                        %endif
                    </div>
                %endif    
            </form>
        </div>
    </div>
    %if tool.help:
        <div class="toolHelp">
            <div class="toolHelpBody">
                 %if tool.has_multiple_pages:
                    ${tool.help_by_page[tool_state.page]}
                 %else:
                    ${tool.help}
                %endif
            </div>        
        </div>
    %endif
</body>

<script type="text/javascript">
##For Drilldown Parameters adds expand/collapse buttons and collapses collapsed elements
   $( function() {
       $( 'li > ul' ).each( function( i ) {
           if ( $( this )[0].className == 'toolParameterExpandableCollapsable' )
           {
               var parent_li = $( this ).parent( 'li' );
               var sub_ul = $( this ).remove();
               parent_li.find( 'span' ).wrapInner( '<a/>' ).find( 'a' ).click( function() {
                 sub_ul.toggle();
                 $( this )[0].innerHTML = ( sub_ul[0].style.display=='none' ) ? '[+]' : '[-]';
               });
               parent_li.append( sub_ul );
           }
       });
       $( 'ul ul' ).each( function(i) {
           if ( $( this )[0].className == 'toolParameterExpandableCollapsable' && this.attributes.getNamedItem( 'default_state' ).value == 'collapsed' )
           {
               $( this ).hide();
           }
       });
   });

##inserts the Select All / Unselect All buttons for checkboxes
$( function() {
    $("div.checkUncheckAllPlaceholder").each( function( i ) {
        $( this )[0].innerHTML = '<a class="action-button" onclick="checkUncheckAll( \'' + this.attributes.getNamedItem( 'checkbox_name' ).value + '\', 1 );"><span>Select All</span></a> <a class="action-button" onclick="checkUncheckAll( \'' + this.attributes.getNamedItem( 'checkbox_name' ).value + '\', 0 );"><span>Unselect All</span></a>';
    });
});

</script>

</html>
