<%inherit file="/base.mako"/>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script>
        $( document ).ready( function(){
            $("div#postRedirect").hide();
            $("form#postRedirectForm").submit();
        });
    </script>
</%def>

<%def name="title()">Post Biostar Question</%def>

<div class="infomessagelarge">
    <p>You are now being forwarded to Biostar.<p>
    <div id="postRedirect">
        <p>If you are not automatically forwarded, click the button below:<p>
        <form id="postRedirectForm" action="${post_url}" method="post" >
            %for input_name, input_value in form_inputs.items():
                <input type="hidden" name="${input_name}" value="${input_value | h}">
            %endfor
                <input type="submit" name="GalaxySubmitPostRedirectForm" id='GalaxySubmitPostRedirectForm' value="Click Here">
        </form>
    </div>
</div>
