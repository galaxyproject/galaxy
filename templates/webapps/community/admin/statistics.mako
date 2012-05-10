<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Tool shed statistics generated on ${trans.app.shed_counter.generation_time}</div>
        <form name="regenerate_statistics" id="regenerate_statistics" action="${h.url_for( controller='admin', action='regenerate_statistics', webapp='community' )}" method="post" >
            <div class="form-row">
                <table class="grid">
                    <tr>
                        <th>Item</th>
                        <th>Count</th>
                    </tr>
                    <tr>
                        <td>Total repositories</td>
                        <td>${trans.app.shed_counter.repositories}</td>
                    </tr>
                    <tr>
                        <td>Empty repositories</td>
                        <td>${trans.app.shed_counter.new_repositories}</td>
                    </tr>
                    <tr>
                        <td>Deleted repositories</td>
                        <td>${trans.app.shed_counter.deleted_repositories}</td>
                    </tr>
                    <tr>
                        <td>Valid tools</td>
                        <td>${trans.app.shed_counter.valid_tools}</td>
                    </tr>
                    <tr>
                        <td>Invalid tools</td>
                        <td>${trans.app.shed_counter.invalid_tools}</td>
                    </tr>
                    <tr>
                        <td>Workflows</td>
                        <td>${trans.app.shed_counter.workflows}</td>
                    </tr>
                    <tr>
                        <td>Proprietary datatypes</td>
                        <td>${trans.app.shed_counter.proprietary_datatypes}</td>
                    </tr>
                    <tr>
                        <td>Total clones</td>
                        <td>${trans.app.shed_counter.total_clones}</td>
                    </tr>
                </table>
            </div>
            <div class="form-row">
                <input type="submit" name="regenerate_statistics_button" value="Regenerate statistics"/>
            </div>
        </form>
    </div>
</div>
