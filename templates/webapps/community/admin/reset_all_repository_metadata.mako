<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Reset metadata on each change set of the repositories in this tool shed</div>
        <form name="reset_all_repository_metadata" id="reset_all_repository_metadata" action="${h.url_for( controller='admin', action='reset_all_repository_metadata' )}" method="post" >
            <div class="form-row">
                Click the button below to reset metadata on each change set of the repositories in this tool shed.
            </div>
            <div class="form-row">
                <input type="submit" name="reset_all_repository_metadata_button" value="Reset all repository metadata"/>
            </div>
        </form>
    </div>
</div>
