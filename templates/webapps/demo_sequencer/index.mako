<%inherit file="/base.mako"/>

## Render a message - can't import because we don't support language encoding here
<%def name="render_message( message, status='done' )">
    <div class="${status}message">${message}</div>
    <br/>
</%def>

%if message:
    ${render_message( message, status )}
%endif

<table border="0" align="center" valign="center" cellpadding="5" cellspacing="5">
    <tr><td><img src="/static/images/sequencer.png" alt="Sequencer" /></td></tr>
    <tr>
        <td>
            %if title:
                <h2>${title}</h2>
            %else:
                <h2>&nbsp;</h2>
            %endif
        </td>
    </tr>
</table>

%if redirect_action != 'exit':
    <script type="text/javascript">
        top.location.href = "${h.url_for( controller='common', action='index', redirect_action=redirect_action, JobId=JobId, sample_id=sample_id, field_0=field_0 )}";;
    </script>
%endif
