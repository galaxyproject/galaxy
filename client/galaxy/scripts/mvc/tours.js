/**
 *  This is the primary galaxy tours definition, currently only used for
 *  rendering a tour menu.
 *
 *  For now it's intended to be plunked into the center display a-la
 *  Galaxy.app.display, but we could use a modal as well for more flexibility.
 *
 *  DBTODO - This is downright backbone abuse, rewrite it.
 */

define([],function() {

    var Tour = Backbone.Model.extend({
      urlRoot: '/api/tours',
    });

    var Tours = Backbone.Collection.extend({
      url: '/api/tours',
      model: Tour,
    });

    var ToursView = Backbone.View.extend({
        // initialize
        initialize: function(options) {
            var self = this;
            this.setElement('<div/>');
            this.model = new Tours()
            this.model.fetch({
              success: function( model ){
                console.log(model);
                self.render();
              },
              error: function( model, response ){
                // Do something.
                console.error("Failed to fetch tours.");
              }
            });
        },

        render: function(){
            var tpl = _.template([
                "<h2>Available Galaxy Tours</h2>",
                "<ul>",
                '<% _.each(tours, function(tour) { %>',
                    '<li>',
                        '<a href="#" class="tourItem" data-tour.id=<%- tour.id %>>',
                            '<%- tour.id %>',
                        '</a>',
                        '- <%- tour.attributes.description %>',
                    '</li>',
                '<% }); %>',
                "</ul>"].join(''));
            this.$el.html(tpl({tours: this.model.models, Galaxy: Galaxy})).on("click", ".tourItem", function(e){
                Galaxy.app.giveTour($(this).data("tour.id"));
            });
        },


    });

    return {ToursView: ToursView}
});
