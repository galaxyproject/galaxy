<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Tool shed statistics generated on ${trans.app.shed_counter.generation_time}</div>
        <form name="regenerate_statistics" id="regenerate_statistics" action="${h.url_for( controller='admin', action='regenerate_statistics' )}" method="post" >
            <div class="form-row">
                <table class="grid">
                    <tr>
                        <th>Item</th>
                        <th>Count</th>
                    </tr>
                    <tr>
                        <td>Total repositories</td>
                        <td>${trans.app.shed_counter.repositories | h}</td>
                    </tr>
                    <tr>
                        <td>Unique owners</td>
                        <td>${trans.app.shed_counter.unique_owners | h}</td>
                    </tr>
                    <tr>
                        <td>Deprecated repositories</td>
                        <td>${trans.app.shed_counter.deprecated_repositories | h}</td>
                    </tr>
                    <tr>
                        <td>Deleted repositories</td>
                        <td>${trans.app.shed_counter.deleted_repositories | h}</td>
                    </tr>
                    <tr>
                        <td>Valid tools</td>
                        <td>${trans.app.shed_counter.unique_valid_tools | h}</td>
                    </tr>
                    <tr>
                        <td>Valid versions of tools</td>
                        <td>${trans.app.shed_counter.valid_versions_of_tools | h}</td>
                    </tr>
                    <tr>
                        <td>Invalid versions of tools</td>
                        <td>${trans.app.shed_counter.invalid_versions_of_tools | h}</td>
                    </tr>
                    <tr>
                        <td>Custom datatypes</td>
                        <td>${trans.app.shed_counter.custom_datatypes | h}</td>
                    </tr>
                    <tr>
                        <td>Total clones</td>
                        <td>${trans.app.shed_counter.total_clones | h}</td>
                    </tr>
                </table>
            </div>
            <div class="form-row">
                <input type="submit" name="regenerate_statistics_button" value="Regenerate statistics"/>
            </div>
        </form>
    </div>
</div>
