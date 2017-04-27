<html lang="sv-SE">
  <head>
    <title>Logga in</title>
  </head>
    <body>
        <div class="login_form" class="block">
            <form action="${action}" method="post" class="login form">
                <input type="hidden" name="query" value="${query}"/>
                <input type="hidden" name="acr_values" value="${acr}"/>
                <table>
                    <tr>
                        <td>Användarnamn</td>
                        <td><input type="text" name="login"
                                   value="${login}"/></td>
                    </tr>
                    <tr>
                        <td>Lösenord</td>
                        <td><input type="password" name="password"
                        value="${password}"/></td>
                    </tr>
                    <tr>
                        <td></td>
                        <td><input type="submit" name="form.commit"
                                value="Log In"/></td>
                    </tr>
                </table>
            </form>
            % if logo_uri:
                <img src="${logo_uri}" alt="Client logo">
            % endif
            % if policy_uri:
                <a href="${policy_uri}"><b>Client policy</b></a>
            % endif
        </div>
    </body>
</html>
