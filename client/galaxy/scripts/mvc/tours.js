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

    var gxy_root = typeof Galaxy === "undefined" ? '/' : Galaxy.root;

    var tour_opts = { storage: window.sessionStorage,
                      onEnd: function(){
                          sessionStorage.removeItem('activeGalaxyTour');
                      },
                      delay: 150, // Attempts to make it look natural
                      orphan:true
    };

    var hooked_tour_from_data = function(data){
        _.each(data.steps, function(step) {
            if (step.preclick){
                step.onShow= function(){
                    _.each(step.preclick, function(preclick){
                        // TODO: click delay between clicks
                        $(preclick).click();
                    });
                };
            }
            if (step.postclick){
                step.onHide = function(){
                    _.each(step.postclick, function(postclick){
                        // TODO: click delay between clicks
                        $(postclick).click();
                    });
                };
            }
            if (step.textinsert){
                // Have to manually trigger a change here, for some
                // elements which have additional logic, like the
                // upload input box
                step.onShown= function(){
                    $(step.element).val(step.textinsert).trigger("change");
                };
            }
        });
        return data;
    };

    var TourItem = Backbone.Model.extend({
      urlRoot: gxy_root + 'api/tours',
    });

    var Tours = Backbone.Collection.extend({
      url:  gxy_root + 'api/tours',
      model: TourItem,
    });


    var giveTour =  function(tour_id){
        var url = gxy_root + 'api/tours/' + tour_id;
        $.getJSON( url, function( data ) {
            // Set hooks for additional click and data entry actions.
            var tourdata = hooked_tour_from_data(data);
            sessionStorage.setItem('activeGalaxyTour', JSON.stringify(data));
            // Store tour steps in sessionStorage to easily persist w/o hackery.
            var tour = new Tour(_.extend({
                steps: tourdata.steps,
            }, tour_opts));
            // Always clean restart, since this is a new, explicit giveTour execution.
            tour.init();
            tour.goTo(0);
            tour.restart();
        });
    };
    var ToursView = Backbone.View.extend({
        // initialize
        initialize: function() {
            var self = this;
            this.setElement('<div/>');
            this.model = new Tours();
            this.model.fetch({
              success: function(){
                self.render();
              },
              error: function(){
                // Do something.
                console.error("Failed to fetch tours.");
              }
            });
        },

        render: function(){
            var tpl = _.template([
                "<h2>Galaxy Tours</h2>",
                "<p>This page presents a list of interactive tours available on this Galaxy server.  ",
                "Select any tour to get started (and remember, you can click 'End Tour' at any time).</p>",
                "<ul>",
                '<% _.each(tours, function(tour) { %>',
                    '<li>',
                        '<a href="/tours/<%- tour.id %>" class="tourItem" data-tour.id=<%- tour.id %>>',
                            '<%- tour.attributes.name || tour.id %>',
                        '</a>',
                        ' - <%- tour.attributes.description || "No description given." %>',
                    '</li>',
                '<% }); %>',
                "</ul>"].join(''));
            this.$el.html(tpl({tours: this.model.models})).on("click", ".tourItem", function(e){
                e.preventDefault();
                giveTour($(this).data("tour.id"));
            });
        }
    });

    return {ToursView: ToursView,
            hooked_tour_from_data: hooked_tour_from_data,
            tour_opts: tour_opts,
            giveTour: giveTour};
});
