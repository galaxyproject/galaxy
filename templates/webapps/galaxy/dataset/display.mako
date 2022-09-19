## Because HDAs do not have many of the properties that other sharable items have, we need to override most of the default code for display.
<%inherit file="/display_base.mako"/>
<%namespace file="/display_common.mako" import="*" />
<%namespace file="/tagging_common.mako" import="render_individual_tagging_element, render_community_tagging_element" />

<%def name="javascript_app()">
    <!-- display.mako javascript_app() -->
    ${parent.javascript_app()}

    ## If data is chunkable, use JavaScript for display.
    %if item.datatype.CHUNKABLE:
        <script type="text/javascript">
            config.addInitialization(function() {
                console.log("display.mako", "chunkable init");

                // Use tabular data display progressively by deleting data from page body
                // and then showing dataset view.
                var item = ${h.dumps(item.to_dict())};
                var chunk_url = "${h.url_for( controller='/dataset', action='display', dataset_id=trans.security.encode_id( item.id ))}";
                var first_data_chunk = ${first_chunk};

                var dataset_config = Object.assign({}, item, {
                    chunk_url: chunk_url,
                    first_data_chunk: first_data_chunk
                });
                var target = '.page-body';

                $(target).children().remove();
                window.bundleEntries.createTabularDatasetChunkedView({
                    dataset_config: dataset_config,
                    parent_elt: target
                });
            })
        </script>
    %endif
</%def>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=True
    self.message_box_visible=False
    self.active_view="user"
    self.overlay_visible=False
%>
</%def>

<%def name="title()">
    ${get_class_display_name( item.__class__ )} | ${get_item_name( item ) | h}
</%def>

<%def name="render_item_links( data )">
    ## Provide links to save data and import dataset.
    <a href="${h.url_for( controller='/dataset', action='display', dataset_id=trans.security.encode_id( data.id ), to_ext=data.ext )}"
        class="icon-button disk"
        title="Save dataset"></a>
    <a href="${h.url_for( controller='/dataset', action='imp', dataset_id=trans.security.encode_id( data.id ) )}"
        class="icon-button import"
        title="Import dataset"></a>
</%def>

## Renders dataset content. Function is used to render data in stand-along page and to provide content for embedded datasets as well.
<%def name="render_item( data, data_to_render )">
    ${ render_deleted_data_message( data ) }
    %if data_to_render:
        %if truncated:
            <div class="warningmessagelarge">
                 This dataset is large and only the first megabyte is shown below. |
                 <a href="${h.url_for( controller='dataset', action='display_by_username_and_slug', username=data.history.user.username, slug=trans.security.encode_id( data.id ), preview=False )}">Show all</a>
            </div>
        %endif
        ## TODO: why is the default font size so small?
        <pre style="font-size: 135%">${ data_to_render | h }</pre>
    %elif data.get_size() == 0:
        <i>Dataset is empty.</i>
    %else:
        <i>Problem displaying dataset content.</i>
    %endif
</%def>

<%def name="render_deleted_data_message( data )">
    %if data.deleted:
        <div class="errormessagelarge" id="deleted-data-message">
            You are viewing a deleted dataset.
            %if data.history and data.history.user == trans.get_user():
                <br />
                <a href="javascript:void(0)" role="button" onclick="$.ajax( {type: 'GET', cache: false, url: '${h.url_for( controller='dataset', action='undelete_async', dataset_id=trans.security.encode_id( data.id ) )}', dataType: 'text', contentType: 'text/html', success: function( data, textStatus, jqXHR ){ if (data == 'OK' ){ $( '#deleted-data-message' ).slideUp( 'slow' ) } else { alert( 'Undelete failed.' ) } }, error: function( data, textStatus, jqXHR ){ alert( 'Undelete failed.' ); } } );">Undelete</a>
            %endif
        </div>
    %endif
</%def>

<%def name="center_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
                ${get_class_display_name( item.__class__ )}
            | ${get_item_name( item ) | h}
        </div>
    </div>

    <div class="unified-panel-body">
        <div style="overflow: auto; height: 100%;">
            <div class="page-body p-3">
                <div style="float: right">
                    ${self.render_item_links( item )}
                </div>
                <div>
                    ${self.render_item_header( item )}
                </div>

                ${self.render_item( item, item_data )}
            </div>
        </div>
    </div>
</%def>

<%def name="right_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            About this ${get_class_display_name( item.__class__ )}
        </div>
    </div>

    <div class="unified-panel-body">
        <div style="overflow: auto; height: 100%;">
            <div style="padding: 10px;">
                <h4>Author</h4>

                <p>${item.history.user.username | h}</p>

                <div><img src="https://secure.gravatar.com/avatar/${h.md5(item.history.user.email)}?d=identicon&s=150"></div>

                ## Page meta.

                ## No links for datasets right now.

                ## Tags.
                <p>
                <h4>Tags</h4>
                <p>
                ## Community tags.
                <div>
                    Community:
                    ${render_community_tagging_element( tagged_item=item, tag_click_fn='community_tag_click', use_toggle_link=False )}
                    %if len ( item.tags ) == 0:
                        none
                    %endif
                </div>
                ## Individual tags.
                <p>
                <div>
                    Yours:
                    ${render_individual_tagging_element( user=trans.get_user(), tagged_item=item, elt_context='view.mako', use_toggle_link=False, tag_click_fn='community_tag_click' )}
                </div>
            </div>
        </div>
    </div>

</%def>
