<%inherit file="/base.mako"/>

<div class="toolForm">
    <form name="change_password" id="change_password" action="${h.url_for( controller='user', action='change_password' )}" method="post" >
        <div class="toolFormTitle">Change Password</div>
        %if token:
            <input type="hidden" name="token" value="${token|h}"/>
        %else:
            <input type="hidden" name="id" value="${id|h}"/>
            <div class="form-row">
                <label>Current password:</label>
                <input type="password" name="current" value="" size="40"/>
            </div>
        %endif
        <div class="form-row">
            <label>New password:</label>
            <input id="password_input" type="password" name="password" value="" size="40"/>
        </div>
        <div class="progress">
            <div id="password_strength" class="progress-bar" role="progressbar">
                Strength
            </div>
        </div>
        <div class="form-row">
            <label>Confirm:</label>
            <input type="password" name="confirm" value="" size="40"/>
        </div>
        <div class="form-row">
            <input type="submit" name="change_password_button" value="Save"/>
        </div>
    </form>
</div>

<script>
var pwInput = document.getElementById('password_input');
pwInput.onkeyup = function() {
    var pw = pwInput.value;
    var progress_bar = document.getElementById('password_strength');

    var strongPasswordRegex = new RegExp("^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#\$%\^&\*])(?=.{8,})");
    var mediumPasswordRegex = new RegExp("^(((?=.*[a-z])(?=.*[A-Z]))|((?=.*[a-z])(?=.*[0-9]))|((?=.*[A-Z])(?=.*[0-9])))(?=.{6,})");

    if (strongPasswordRegex.test(pw)) {
        progress_bar.style.backgroundColor = 'lightgreen';
        progress_bar.style.width = '100%';
    } else if (mediumPasswordRegex.test(pw)) {
        progress_bar.style.backgroundColor = 'orange';
        progress_bar.style.width = '60%';
    } else {
        progress_bar.style.backgroundColor = 'red';
        progress_bar.style.width = '30%';
    }
};
</script>