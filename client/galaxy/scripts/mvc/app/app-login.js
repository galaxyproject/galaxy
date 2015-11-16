define([ 'utils/utils' ], function( Utils ) {
    return {
        center: Backbone.View.extend({
            initialize: function() {
                this.setElement( Utils.iframe( Galaxy.root + 'static/welcome.html' ) );
            }
        }),
        right: Backbone.View.extend({
            initialize: function() {
                this.components = {
                    header: {
                        title: 'Login required'
                    }
                }
                this.setElement( Utils.iframe( Galaxy.root + 'user/login' ) );
            }
        })
    }
});