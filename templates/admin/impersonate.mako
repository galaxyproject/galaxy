<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

%if emails:
    <div class="toolForm">
        <div class="toolFormTitle">Impersonate another user</div>
        <div class="toolFormBody">
        <form name="impersonate" id="impersonate" action="${h.url_for( controller='admin', action='impersonate' )}" method="post" >
            <div class="form-row">
                <label>
                    User to impersonate:
                </label>
                <select name="email" class='text-and-autocomplete-select'>
                    %for email in emails:
                        <option>${email}</option>
                    %endfor
                </select>
            </div>
            <div class="form-row">
                <input type="submit" name="impersonate_button" value="Impersonate"/>
            </div>
        </form>
        </div>
    </div>
%endif
