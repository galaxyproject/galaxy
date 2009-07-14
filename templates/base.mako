<% _=n_ %>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>

<head>
<title>${self.title()}</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
${self.stylesheets()}
${self.javascripts()}
</head>

    <body>
        ${next.body()}
    </body>
</html>

## Default title
<%def name="title()"></%def>

## Default stylesheets
<%def name="stylesheets()">
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
</%def>

## Default javascripts
<%def name="javascripts()">
  ## <!--[if lt IE 7]>
  ## <script type='text/javascript' src="/static/scripts/IE7.js"> </script>
  ## <![endif]-->
  <script type="text/javascript" src="${h.url_for('/static/scripts/jquery.js')}"></script>
  <script type="text/javascript" src="${h.url_for('/static/scripts/galaxy.base.js')}"></script>


</%def>

<script type="text/javascript">
$( function() {
    $( "select[refresh_on_change='true']").change( function() {
        var refresh = false;
        var refresh_on_change_values = $( this )[0].attributes.getNamedItem( 'refresh_on_change_values' )
        if ( refresh_on_change_values ) {
            refresh_on_change_values = refresh_on_change_values.value.split( ',' );
            var last_selected_value = $( this )[0].attributes.getNamedItem( 'last_selected_value' );
            for( i= 0; i < refresh_on_change_values.length; i++ ) {
                if ( $( this )[0].value == refresh_on_change_values[i] || ( last_selected_value && last_selected_value.value == refresh_on_change_values[i] ) ){
                    refresh = true;
                    break;
                }
            }
        }
        else {
            refresh = true;
        }
        if ( refresh ){
            $( ':file' ).each( function() {
                var file_value = $( this )[0].value;
            } );
            $( "#edit_form" ).submit();
        }
    });
});
</script>