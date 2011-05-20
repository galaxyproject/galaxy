<%def name="common_javascripts(repository)">
    <script type="text/javascript">
        $(function(){
            $("#tree").ajaxComplete(function(event, XMLHttpRequest, ajaxOptions) {
                _log("debug", "ajaxComplete: %o", this); // dom element listening
            });
            // --- Initialize sample trees
            $("#tree").dynatree({
                title: "${repository.name}",
                rootVisible: true,
                minExpandLevel: 0, // 1: root node is not collapsible
                persist: false,
                checkbox: true,
                selectMode: 3,
                onPostInit: function(isReloading, isError) {
                    //alert("reloading: "+isReloading+", error:"+isError);
                    logMsg("onPostInit(%o, %o) - %o", isReloading, isError, this);
                    // Re-fire onActivate, so the text is updated
                    this.reactivate();
                }, 
                fx: { height: "toggle", duration: 200 },
                // initAjax is hard to fake, so we pass the children as object array:
                initAjax: {url: "${h.url_for( controller='repository', action='open_folder' )}",
                           dataType: "json", 
                           data: { repository_id: "${trans.security.encode_id( repository.id )}", key: "${repository.repo_path}" },
                },
                onLazyRead: function(dtnode){
                    dtnode.appendAjax({
                        url: "${h.url_for( controller='repository', action='open_folder' )}", 
                        dataType: "json",
                        data: { repository_id: "${trans.security.encode_id( repository.id )}", key: dtnode.data.key },
                    });
                },
                onSelect: function(select, dtnode) {
                    // Display list of selected nodes
                    var selNodes = dtnode.tree.getSelectedNodes();
                    // convert to title/key array
                    var selKeys = $.map(selNodes, function(node){
                        return node.data.key;
                    });
                    // The following is used only in the upload form.
                    document.upload_form.upload_point.value = selKeys[0];
                },
                onActivate: function(dtnode) {
                    // TODO: certainly not ideal - find a better way to display the file contents.
                    var cell = $("#file_contents");
                    var selected_value;
                    if (dtnode.data.key == 'root') {
                        selected_value = "${repository.repo_path}/";
                    } else {
                        selected_value = dtnode.data.key;
                    };
                    if (selected_value.charAt(selected_value.length-1) != '/') {
                        // Make ajax call
                        $.ajax( {
                            type: "POST",
                            url: "${h.url_for( controller='repository', action='get_file_contents' )}",
                            dataType: "json",
                            data: { file_path: selected_value },
                            success : function ( data ) {
                                cell.html( '<label>'+data+'</label>' )
                            }
                        });
                    } else {
                        cell.html( '' );
                    };
                },
            });
        });
    </script>
</%def>

<%def name="render_clone_str( repository )">
    <%
        protocol, base = trans.request.base.split( '://' )
        if trans.user:
            username = '%s@' % trans.user.username
        else:
            username = ''
        clone_str = '%s://%s%s/repos/%s/%s' % ( protocol, username, base, repository.user.username, repository.name )
    %>
    hg clone <a href="${clone_str}">${clone_str}</a>
</%def>