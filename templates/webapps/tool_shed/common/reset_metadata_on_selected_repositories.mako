<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="common_misc_javascripts" />

<%def name="javascripts()">
    ${parent.javascripts()}
    ${common_misc_javascripts()}
</%def>

%if message:
    ${render_msg( message, status )}
%endif

<style type="text/css">
.state-ok {
    background: #aff1af;
}
.state-error {
    background: #f9c7c5;
}
.state-queued {
    background: #eee;
}
.state-running {
    background: #ffc;
}
</style>
<div class="warningmessage">
    Resetting metadata may take a while because this process clones each change set in each selected repository's change log to a temporary location on disk.
    Wait until this page redirects after clicking the <b>Reset metadata on selected repositories</b> button, as doing anything else will not be helpful.  Watch 
    the tool shed paster log to pass the time if necessary.
</div>

<div class="toolForm">
    <div class="toolFormTitle">Reset all metadata on each selected repository</div>
        <%
            if trans.user_is_admin():
                controller = 'admin'
                action = 'reset_metadata_on_selected_repositories_in_tool_shed'
            else:
                controller = 'repository'
                action = 'reset_metadata_on_my_writable_repositories_in_tool_shed'
        %>
        <form name="reset_metadata_on_selected_repositories" id="reset_metadata_on_selected_repositories" action="${h.url_for( controller=controller, action=action )}" method="post" >
            <div class="form-row">
                Check each repository for which you want to reset metadata.  Repository names are followed by owners in parentheses.
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <input type="checkbox" id="checkAll" name="select_all_repositories_checkbox" value="true" onclick="checkAllRepositoryIdFields(1);"/><input type="hidden" name="select_all_repositories_checkbox" value="true"/><b>Select/unselect all repositories</b>
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                ${repositories_select_field.get_html()}
            </div>
            <div style="clear: both"></div>
            <div class="form-row">
                <input type="submit" id="reset_metadata_button" name="reset_metadata_on_selected_repositories_button" value="Reset metadata on selected repositories"/>
            </div>
        </form>
    </div>
</div>
<script type="text/javascript">
    $('#reset_metadata_on_selected_repositories').submit(function(f) {
        f.preventDefault();
        var repository_ids = Array()
        $('input:checked').each(function() {
            if ($(this).id != 'checkAll') {
                var repository_id = $(this).attr('value');
                repository_ids.push(repository_id);
                repo_div = $(this).parent();
                repo_div.attr('class', 'state-queued');
            }
        });
        for (var i = 0; i < repository_ids.length; i++) {
            repository_id = repository_ids[i];
            repo_elem = $("[value=" + repository_id + "]");
            repo_div = repo_elem.parent();
            repo_div.attr('class', 'state-running');
            $.ajax({
                type: 'POST',
                url: '${h.url_for('/api/repositories/reset_metadata_on_repository')}',
                data: { repository_id: repository_id },
                dataType: "json"
            }).always(function (data) {
                repo_div.attr('class', 'state-' + data['status']);
                if (data['status'] == 'error') {
                    repo_div.attr('title', data['repository_status'][0]);
                }
            });
        }; 
    });
</script>