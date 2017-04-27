<%inherit file="root.mako" />
<div class="header">
    <h1><a href="/">${title}</a></h1>
</div>
<div class="login_form" class="block">
    <form action="${action}" method="post" class="login form">
        <input type="hidden" name="query" value="${query}"/>
        <input type="hidden" name="acr_values" value="${acr}"/>
        <table>
            <tr>
                <td>${login_title}</td>
                <td><input type="text" name="login" value="${login}"/></td>
            </tr>
            <tr>
                <td>${passwd_title}</td>
                <td><input type="password" name="password"
                value="${password}"/></td>
            </tr>
            <tr>
                </td>
                <td><input type="submit" name="form.commit"
                        value="${submit_text}"/></td>
            </tr>
        </table>
    </form>
    % if logo_uri:
        <img src="${logo_uri}" alt="Client logo">
    % endif
    % if policy_uri:
        <a href="${policy_uri}"><strong>Client&#39;s Policy</strong></a>
    % endif
    % if tos_uri:
        <a href="${tos_uri}"><strong>Client&#39;s Terms of Service</strong></a>
    % endif
</div>

<%def name="add_js()">
    <script type="text/javascript">
        $(document).ready(function() {
            bookie.login.init();
        });
    </script>
</%def>
