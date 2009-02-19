<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='library', action='browse_library', id=library_id )}"><span>Browse this library</span></a>
    </li>
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

%if liit:
    <form name="library_item_info_template_edit" action="${h.url_for( controller='library', action='library_item_info_template' )}" method="post" >
        <div class="toolForm">
            <div class="toolFormTitle">Edit Library Item Info Template</div>
            <div class="toolFormBody">
                <input type="hidden" name="id" value="${liit.id}"/>
                <input type="hidden" name="set_element_count" value="${new_element_count}"/>
                <div class="form-row">
                    <label>Field name:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="name" value="${liit.name}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Information text:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="description" value="${liit.description}" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
            </div>
        </div>
        <div class="toolForm">
            <div class="toolFormBody">
                %for template_element in liit.elements:
                    <div class="toolFormTitle">Edit Element</div>
                    <input type="hidden" name="element_ids" value="${template_element.id}"/>
                    <div class="form-row">
                        <label>Name:</label>
                        <div style="float: left; width: 250px; margin-right: 10px;">
                            <input type="text" name="element_name_${template_element.id}" value="${template_element.name}" size="40"/>
                        </div>
                        <div style="clear: both"></div>
                    </div>
                    <div class="form-row">
                        <label>Description:</label>
                        <div style="float: left; width: 250px; margin-right: 10px;">
                            <input type="text" name="element_description_${template_element.id}" value="${template_element.description}" size="40"/>
                        </div>
                        <div style="clear: both"></div>
                    </div>
                %endfor
                %for element_count in range( new_element_count ):
                    <div class="form-row">
                        <div class="toolFormTitle">Create Element ${1+element_count}</div>
                        <div class="form-row">
                            <label>Name:</label>
                            <div style="float: left; width: 250px; margin-right: 10px;">
                                <input type="text" name="new_element_name_${element_count}" value="" size="40"/>
                            </div>
                            <div style="clear: both"></div>
                        </div>
                        <div class="form-row">
                            <label>Description:</label>
                            <div style="float: left; width: 250px; margin-right: 10px;">
                                <input type="text" name="new_element_description_${element_count}" value="" size="40"/>
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    </div>
                %endfor
                <div class="form-row">
                    <label>Add additional elements:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="new_element_count" value="0" size="3"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <input type="submit" name="liit_edit_button" value="Save"/>
            </div>
        </div>
    </form>
    <p/>
%else:
    <form name="library_item_info_template_new" action="${h.url_for( controller='library', action='library_item_info_template' )}" method="post" >
        <div class="toolForm">
            <div class="toolFormTitle">Create information template for ${library_item_desc} ${library_item_name}</div>
            <div class="toolFormBody">
                %if library_id:
                    <input type="hidden" name="library_id" value="${library_id}"/>
                %elif library_dataset_id:
                    <input type="hidden" name="library_dataset_id" value="${library_dataset_id}"/>
                %elif folder_id:
                    <input type="hidden" name="folder_id" value="${folder_id}"/>
                %elif ldda_id:
                    <input type="hidden" name="ldda_id" value="${ldda_id}"/>
                %endif
                <input type="hidden" name="set_element_count" value="${new_element_count}"/>
                <div class="form-row">
                    <label>Template name:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="name" value="" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <label>Template description:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="description" value="" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
            </div>
        </div>
        <div class="toolForm">
            <div class="toolFormTitle">Create the following template elements</div>
            <div class="toolFormBody">
                %for element_count in range( new_element_count ):
                    <div class="form-row">
                        <b>${1+element_count}) Name:</b>
                        <input type="text" name="new_element_name_${element_count}" value="" size="40"/>
                        <b>Description:</b>
                        <input type="text" name="new_element_description_${element_count}" value="" size="40"/>
                    </div>
                    <div style="clear: both"></div>
                %endfor
            </div>
        </div>
        <div class="toolForm">
            <div class="toolFormBody">
                <div class="form-row">
                    <label>Add additional elements:</label>
                    <div style="float: left; width: 250px; margin-right: 10px;">
                        <input type="text" name="new_element_count" value="0" size="3"/>
                    </div>
                    <div style="clear: both"></div>
                </div>
                <input type="submit" name="liit_create_button" value="Save"/>
            </div>
        </div>
    </form>
    <p/>
%endif
