define(['utils/utils'],
    function( Utils ) {

    // create form view
    return Backbone.View.extend({
        // initialize
        initialize: function( options ) {
            // configure options
            this.options = Utils.merge( options, {} );

            // set element
            this.setElement( this._template() );

            /*if trans.app.config.require_login and not trans.user:
                center_url = h.url_for( controller='user', action='login' )
            elif tool_id is not None:
                center_url = h.url_for( 'tool_runner', tool_id=tool_id, from_noframe=True, **params )
            elif workflow_id is not None:
                center_url = h.url_for( controller='workflow', action='run', id=workflow_id )
            elif m_c is not None:
                center_url = h.url_for( controller=m_c, action=m_a )
            else:
                    center_url = h.url_for( controller="root", action="welcome" )*/
            this.$( '#galaxy_main' ).prop( 'src', galaxy_config.root + 'welcome' );
        },

        _template: function() {
            return  '<div style="position: absolute; width: 100%; height: 100%">' +
                        '<iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;"/>' +
                    '</div>';
        }
    });
});
