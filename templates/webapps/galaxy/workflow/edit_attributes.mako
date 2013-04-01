<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">${_('Edit Workflow Attributes')}</%def>

<%def name="stylesheets()">
    ${h.css( "base", "autocomplete_tagging" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "libs/jquery/jquery.autocomplete", "galaxy.autocom_tagging" )}
</%def>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<%def name="body()">
    <div class="toolForm">
        <div class="toolFormTitle">${_('Edit Workflow Attributes')}</div>
        <div class="toolFormBody">
            <form name="edit_attributes" action="${h.url_for(controller='workflow', action='edit_attributes' )}" method="post">
                <input type="hidden" name="id" value="${trans.security.encode_id( stored.id )}"/>
                <div class="form-row">
                    <label>
                        Name:
                    </label>
                    <div style="float: left; width: 225px; margin-right: 10px;">
                        <input type="text" name="name" value="${stored.name}" size="30"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <%namespace file="/tagging_common.mako" import="render_individual_tagging_element" />
                <div class="form-row">
                    <label>
                        Tags:
                    </label>
                    <div style="float: left; width: 265px; margin-right: 10px; border-style: inset; border-width: 1px; margin-left: 2px">
                        <style>
                            .tag-area {
                                border: none;
                            }
                        </style>
                        ${render_individual_tagging_element(user=trans.get_user(), tagged_item=stored, elt_context="edit_attributes.mako", use_toggle_link=False, in_form=True, input_size="25")}
                    </div>
                    <div style="clear: both"></div>
                    <div class="toolParamHelp">Apply tags to make it easy to search for and find items with the same tag.</div>
                </div>
                <div class="form-row">                    
                    <label>
                        Annotation / Notes:
                    </label>
                    <div style="float: left; width: 225px; margin-right: 10px;">
                        <textarea name="annotation" cols="30" rows="2">${annotation}</textarea>
                    </div>
                    <div style="clear: both"></div>
                    <div class="toolParamHelp">Add an annotation notes to a workflow; annotations are available when a workflow is viewed.</div>
                </div>
                <div class="form-row">
                    <input type="submit" name="save" value="${_('Save')}"/>
                </div>
            </form>
        </div>
    </div>
</%def>
