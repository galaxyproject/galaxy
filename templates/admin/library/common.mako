
<%def name="render_template_info( library_item, library_id, widgets, editable=True )">
    <%
        library_item_type = 'unknown type'
        library_item_desc = ''
        if isinstance( library_item, trans.app.model.Library ):
            library_item_type = 'library'
            library_item_desc = 'library'
        elif isinstance( library_item, trans.app.model.LibraryFolder ):
            library_item_type = 'folder'
            library_item_desc = 'folder'
        elif isinstance( library_item, trans.app.model.LibraryDataset ):
            library_item_type = 'library_dataset'
            library_item_desc = 'dataset'
        elif isinstance( library_item, trans.app.model.LibraryDatasetDatasetAssociation ):
            library_item_type = 'library_dataset_dataset_association'
            library_item_desc = 'library dataset'
    %>
    %if widgets:
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Other information about ${library_item_desc} ${library_item.name}</div>
            <div class="toolFormBody">
                %if editable:
                    <form name="edit_info" action="${h.url_for( controller='library_admin', action='edit_template_info', library_id=library_id, num_widgets=len( widgets ) )}" method="post">
                        <input type="hidden" name="library_item_id" value="${library_item.id}"/>
                        <input type="hidden" name="library_item_type" value="${library_item_type}"/>
                        %for i, field in enumerate( widgets ):
                            <div class="form-row">
                                <label>${field[ 'label' ]}</label>
                                ${field[ 'widget' ].get_html()}
                                <div class="toolParamHelp" style="clear: both;">
                                    ${field[ 'helptext' ]}
                                </div>
                                <div style="clear: both"></div>
                            </div>
                        %endfor 
                        <div class="form-row">
                            <input type="submit" name="edit_info_button" value="Save"/>
                        </div>
                    </form>
                %else:
                    %for i, field in enumerate( widgets ):
                        %if field[ 'widget' ].value:
                            <div class="form-row">
                                <label>${field[ 'label' ]}</label>
                                ${field[ 'widget' ].value}
                                <div class="toolParamHelp" style="clear: both;">
                                    ${field[ 'helptext' ]}
                                </div>
                                <div style="clear: both"></div>
                            </div>
                        %endif
                    %endfor
                %endif
            </div>
        </div>
    %endif
</%def>
