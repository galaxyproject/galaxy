<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="javascripts()">
   ${parent.javascripts()}
   ${h.js("libs/jquery/jquery.autocomplete")}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "autocomplete_tagging" )}
</%def>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button"  href="${h.url_for( controller=cntrller, action='browse_requests' )}">Browse requests</a></li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Create a new sequencing request</div>
    %if len( request_type_select_field.options ) < 1:
        There are no request types available for ${trans.user.email | h} to create sequencing requests.
    %else:
        <div class="toolFormBody">
            <form name="create_request" id="create_request" action="${h.url_for( controller='requests_common', action='create_request', cntrller=cntrller )}" method="post" >
                <div class="form-row">
                    <label>Select a request type configuration:</label>
                    ## The request_type_select_field is a SelectField named request_type_id
                    ${request_type_select_field.get_html()}
                    %if cntrller != 'requests_admin':
                        <div class="toolParamHelp" style="clear: both;">
                            Contact the lab manager if you are not sure about the request type configuration.
                        </div>
                    %endif
                </div>
                %if request_type_select_field_selected != 'none':
                    ## If a request_type has been selected, display the associated form using received widgets.
                    %for i, field in enumerate( widgets ):
                        <div class="form-row">
                            <label>${field['label']}</label>
                            ${field['widget'].get_html()}
                            <div class="toolParamHelp" style="clear: both;">
                                ${field['helptext']}
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    %endfor
                    <div class="form-row">
                        <input type="submit" name="create_request_button" value="Save"/>
                        <input type="submit" name="add_sample_button" value="Add samples"/>
                    </div>
                %endif
            </form>
        </div>
    %endif
</div>
