<%inherit file="root.mako" />
<%def name="title()">Log in</%def>

<div class="login_form" class="block">

    <h1>Log in with Javascript</h1>

    <form action="${action}" method="post" class="login form">
        <input type="hidden" name="query" value="${query}"/>
        <input type="hidden" name="acr_values" value="${acr}"/>
        <input type="hidden" id="login_param" name="login_parameter" value=""/>

        <input type="submit" name="form.commit" value="Log In"/>
    </form>
    % if logo_uri:
        <img src="${logo_uri}" alt="Client logo">
    % endif
    % if policy_uri:
        <a href="${policy_uri}"><b>Client policy</b></a>
    % endif
</div>

<script type="text/javascript">
    document.getElementById("login_param").value = "logged_in";
</script>

<%def name="add_js()">
    <script type="text/javascript">
        $(document).ready(function() {
            bookie.login.init();
        });
    </script>
</%def>
