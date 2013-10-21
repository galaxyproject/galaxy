<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<br/><br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button"  href="${h.url_for( controller='userskeys', action='all_users', cntrller=cntrller )}">List users API keys</a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

            <div>
                <div style="clear: both;">
		    SUCCESS. A new API key has been generated.
                </div>
		

                <div style="clear: both;">
                    An API key will allow you to access Galaxy via its web
                    API (documentation forthcoming).  Please note that
                    <strong>this key acts as an alternate means to access
                    your account, and should be treated with the same care
                    as your login password</strong>.
                </div>
            </div>
