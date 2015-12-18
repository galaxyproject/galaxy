/**
 *  This is the primary galaxy tours definition, currently only used for
 *  rendering a tour menu.
 *
 *  For now it's intended to be plunked into the center display a-la
 *  Galaxy.app.display, but we could use a modal as well for more flexibility.
 *
 *  DBTODO - This is downright backbone abuse, rewrite it.
 */

define(['libs/bootstrap-tour'],function(BootstrapTour) {

    var TourItem = Backbone.Model.extend({
      urlRoot: '/api/tours',
    });

    var Tours = Backbone.Collection.extend({
      url: '/api/tours',
      model: TourItem,
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
            var self = this;
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
                self.giveTour($(this).data("tour.id"));
            });
        },

        // DBTODO: THIS SHOULD PROBABLY NOT BE HERE -- but where?
        giveTour: function(tour_id){
            var url = Galaxy.root + 'api/tours/' + tour_id;
            $.getJSON( url, function( data ) {
                // Set hooks for additional click and data entry actions.
                _.each(data.steps, function(step) {
                    if (step.preclick){
                        step.onShow= function(){$(step.preclick).click()};
                    }
                    if (step.postclick){
                        step.onHide = function(){$(step.postclick).click()};
                    }
                    if (step.textinsert){
                        // Have to manually trigger a change here, for some
                        // elements which have additional logic, like the
                        // upload input box
                        step.onShown= function(){$(step.element).val(step.textinsert).trigger("change")};
                    }
                });
                // Store tour steps in sessionStorage to easily persist w/o hackery.
                sessionStorage.setItem('activeGalaxyTour', data);
                var tour = new Tour({
                    orphan: true,
                    debug: true, // REMOVE ME WHEN DONE DEBUGGING
                    steps: data.steps
                });
                // Always clean restart, since this is a new, explicit giveTour execution.
                tour.init();
                tour.goTo(0);
                tour.restart();
            });
        },


    });

    return {ToursView: ToursView}
});
