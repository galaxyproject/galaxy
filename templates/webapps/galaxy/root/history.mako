<%inherit file="/base.mako"/>

<%def name="title()">
    ${_('Galaxy History')}
</%def>

<%namespace file="/history/history_panel.mako" import="bootstrapped_history_panel" />

## -----------------------------------------------------------------------------
<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        body.historyPage {
            margin: 0px;
            padding: 0px;
        }
    </style>
</%def>

## -----------------------------------------------------------------------------
<%def name="javascripts()">
${parent.javascripts()}
${h.js(
    "libs/require",
    "mvc/base-mvc",
    "utils/localization",
    "mvc/user/user-model"
)}
${h.templates( "helpers-common-templates" )}
<script type="text/javascript">
    <%
        user_data = trans.webapp.api_controllers[ 'users' ].show( trans, 'current' )
        #HACK - the above sets the response type
        trans.response.set_content_type( "text/html" )
    %>
    ## bc this is in it's own frame we can't reference the global Galaxy obj or the quotameter's User obj
    window.Galaxy = {};
    Galaxy.currUser = new User(${user_data});
    $(function(){
        $( 'body' ).addClass( 'historyPage' ).addClass( 'history-panel' );
    });
</script>

${bootstrapped_history_panel( history, hdas, selector_to_attach_to='body.historyPage', \
                              show_deleted=show_deleted, show_hidden=show_hidden, hda_id=hda_id )}
</%def>
