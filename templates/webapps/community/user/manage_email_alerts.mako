<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller='repository', action='multi_select_email_alerts', cntrller='repository', webapp=webapp )}">Manage repository alerts</a>
    </li>
    <li>
        <a class="action-button"  href="${h.url_for( controller='user', action='index', cntrller='repository', webapp=webapp )}">User preferences</a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Email alerts for new repositories</div>
    <form name="new_repo_alert" id="new_repo_alert" action="${h.url_for( controller='repository', action='manage_email_alerts', webapp=webapp )}" method="post" >
        <div class="form-row">
            <label>New repository alert:</label>
            ${new_repo_alert_check_box.get_html()}
            <div class="toolParamHelp" style="clear: both;">
                Check the box and click <b>Save</b> to receive email when the first change set is created for a new repository.
            </div>
        </div>
        <div class="form-row">
            <input type="submit" name="new_repo_alert_button" value="Save"/>
        </div>
    </form>
</div>
<p/>
%if email_alert_repositories:
    <div class="toolForm">
        <div class="toolFormTitle">You are registered to receive email alerts for changes to the following repositories</div>
        <div class="form-row">
            <table class="grid">
                <tr>
                    <th>Name</th>
                    <th>Description</th>
                </tr>
                %for repository in email_alert_repositories:
                    <tr>
                        <td>${repository.name}</td>
                        <td>${repository.description}</td>
                    </tr>
                %endfor
            </table>
        </div>
    </div>
    <p/>
%endif

