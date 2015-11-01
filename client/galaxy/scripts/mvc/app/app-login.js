define([], function() {
    return {
        center: Backbone.View.extend({
            initialize: function() {
                this.setElement( '<iframe src="' + Galaxy.root + 'user/login" frameborder="0" style="width: 100%; height: 100%;"/>' );
            }
        })
    }
});