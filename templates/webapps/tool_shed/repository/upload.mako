<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

<%
    is_new = repository.is_new( trans.app )
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/tool_shed/base_panels.mako'
       else:
           return '/base.mako'
%>

<%inherit file="${inherit(context)}"/>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "dynatree_skin/ui.dynatree" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ## ${h.js( "libs/jquery/jquery-ui", "libs/jquery/jquery.cookie", "libs/jquery/jquery.dynatree" )}
    ${common_javascripts(repository)}
    <script type="text/javascript">
    $( function() {
        $( "select[refresh_on_change='true']").change( function() {
            $( "#upload_form" ).submit();
        });
    });
    </script>
</%def>

%if message:
    ${render_msg( message, status )}
%endif

${render_tool_shed_repository_actions( repository=repository)}

<div class="toolForm">
    <div class="toolFormBody">
        <div class="form-row">
            <div class="warningmessage">
                Upload a single file or tarball.  Uploading may take a while, depending upon the size of the file.
                Wait until a message is displayed in your browser after clicking the <b>Upload</b> button below.
            </div>
            <div style="clear: both"></div>
        </div>
    </div>
</div>

<div class="toolForm">
    <div class="toolFormTitle">Repository '${repository.name | h}'</div>
    <div class="toolFormBody">
        <form id="upload_form" name="upload_form" action="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ) )}" enctype="multipart/form-data" method="post">
            <div class="form-row">
                <label>File:</label>
                <div class="form-row-input">
                    <input type="file" name="file_data"/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Url:</label>
                <div class="form-row-input">
                    <input name="url" type="textfield" value="${url | h}" size="40"/>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                     Enter a url to upload your files.  In addition to http and ftp urls, urls that point to mercurial repositories (urls that start
                     with hg:// or hgs://) are allowed.  This mechanism results in the tip revision of an external mercurial repository being added
                     to the Tool Shed repository as a single new changeset.  The revision history of the originating external mercurial repository is
                     not uploaded to the Tool Shed repository.
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <%
                    if uncompress_file:
                        yes_selected = 'selected'
                        no_selected = ''
                    else:
                        yes_selected = ''
                        no_selected = 'selected'
                %>
                <label>Uncompress files?</label>
                <div class="form-row-input">
                    <select name="uncompress_file">
                        <option value="true" ${yes_selected}>Yes
                        <option value="false" ${no_selected}>No
                    </select>
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    Supported compression types are gz and bz2.  If <b>Yes</b> is selected, the uploaded file will be uncompressed.  However,
                    if the uploaded file is an archive that contains compressed files, the contained files will not be uncompressed.  For
                    example, if the uploaded compressed file is some_file.tar.gz, some_file.tar will be uncompressed and extracted, but if
                    some_file.tar contains some_contained_file.gz, the contained file will not be uncompressed.
                </div>
            </div>
            %if not is_new:
                <div class="form-row">
                    <%
                        if remove_repo_files_not_in_tar:
                            yes_selected = 'selected'
                            no_selected = ''
                        else:
                            yes_selected = ''
                            no_selected = 'selected'
                    %>
                    <label>Remove files in the repository (relative to the root or selected upload point) that are not in the uploaded archive?</label>
                    <div class="form-row-input">
                        <select name="remove_repo_files_not_in_tar">
                            <option value="true" ${yes_selected}>Yes
                            <option value="false" ${no_selected}>No
                        </select>
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        This selection pertains only to uploaded tar archives, not to single file uploads.  If <b>Yes</b> is selected, files
                        that exist in the repository (relative to the root or selected upload point) but that are not in the uploaded archive
                        will be removed from the repository.  Otherwise, all existing repository files will remain and the uploaded archive
                        files will be added to the repository.
                    </div>
                </div>
            %endif
            <div class="form-row">
                <label>Change set commit message:</label>
                <div class="form-row-input">
                    %if commit_message:
                        <pre><textarea name="commit_message" rows="3" cols="35">${commit_message | h}</textarea></pre>
                    %else:
                        <textarea name="commit_message" rows="3" cols="35"></textarea>
                    %endif
                </div>
                <div class="toolParamHelp" style="clear: both;">
                    This is the commit message for the mercurial change set that will be created by this upload.
                </div>
                <div style="clear: both"></div>
            </div>
            %if not repository.is_new( trans.app ):
                <div class="form-row" >
                    <label>Contents:</label>
                    <div id="tree" >
                        Loading...
                    </div>
                    <input type="hidden" id="upload_point" name="upload_point" value=""/>
                    <div class="toolParamHelp" style="clear: both;">
                        Select a location within the repository to upload your files by clicking a check box next to the location.  The 
                        selected location is considered the upload point.  If a location is not selected, the upload point will be the 
                        repository root.
                    </div>
                    <div style="clear: both"></div>
                </div>
            %endif
            <div class="form-row">
                <input type="submit" class="primary-button" name="upload_button" value="Upload">
            </div>
        </form>
    </div>
</div>
