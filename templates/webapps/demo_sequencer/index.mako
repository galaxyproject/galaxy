<%inherit file="/base.mako"/>

<%
    import galaxy.util
    titles_list = util.listify( titles )
%>

<%def name="javascripts()">
    ${parent.javascripts()}
    %if redirect_action != 'exit':
    <script type="text/javascript">
        function redirect(){
            top.location.href = "${h.url_for( controller='common', action='index', redirect_action=redirect_action, titles=titles, JobId=JobId, sample_id=sample_id )}";
        }
        function set_redirect(){
            %if redirect_delay:
                setTimeout("redirect()", ${int(redirect_delay)*1000});
            %else:
                setTimeout("redirect()", 2000);
            %endif
        }
    </script>
    %endif
</%def>

## Render a message - can't import because we don't support language encoding here
<%def name="render_message( message, status='done' )">
    <div class="${status}message">${message}</div>
    <br/>
</%def>

%if message:
    ${render_message( message, status )}
%endif

<body onload="set_redirect()">
    <table border="0" align="center" valign="center" cellpadding="5" cellspacing="5">
        <tr><td><img src='static/images/sequencer.png' alt="Sequencer" /></td></tr>
        <tr>
            <td align="center">
                %if titles_list:
                    %for title in titles_list:
                        <h2>${title}</h2>
                    %endfor
                %else:
                    <h2>&nbsp;</h2>
                %endif
            </td>
        </tr>
    </table>
    %if not trans.app.sequencer_actions_registry.authenticated and trans.app.sequencer_actions_registry.browser_login:
        <iframe name="login" id="login" frameborder="0" style="position: absolute; width: 0%; height: 0%;" src="${h.url_for( controller="common", action="login" )}"></iframe>
    %endif
</body>
