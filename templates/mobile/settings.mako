<form id="settings" class="panel" action="${h.url_for( action='settings' )}" method="post">
    
    <div class="toolbar">
        <h1>Settings</h1>
        <a class="back button leftButton" href="#">Cancel</a>
        <input class="button blueButton" type="submit" href="#" value="Save">
    </div>
    
    <div class="pad">
        

            <h2>User information</h2>
            <fieldset>
                <%
                    if t.user:
                        email = t.user.email
                    else:
                        email = ""
                %>
                
                <div class="row">
                    <label>Email</label>
                    <input type="text" name="email" value="${email}">
                </div>
                <div class="row">
                    <label>Password</label>
                    <input type="password" name="password" value ="">
                </div>
            </fieldset>
            %if message:
                <div>${message}</div>
            %endif
    </div>
</form>