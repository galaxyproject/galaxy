/**
 *  This is the primary galaxy tours definition, currently only used for
 *  rendering a tour menu.
 */

import * as BootstrapTour from "libs/bootstrap-tour";
var gxy_root = typeof Galaxy === "undefined" ? "/" : Galaxy.root;

var tourpage_template = `<h2>Galaxy Tours</h2>
<p>This page presents a list of interactive tours available on this Galaxy server.
Select any tour to get started (and remember, you can click 'End Tour' at any time).</p>

<div class="col-12 btn-group" role="group" aria-label="Tag selector">
    <% _.each(tourtagorder, function(tag) { %>
    <button class="btn btn-primary tag-selector-button" tag-selector-button="<%- tag %>">
        <%- tag %>
    </button>
    <% }); %>
</div>

<% _.each(tourtagorder, function(tourtagkey) { %>
<div tag="<%- tourtagkey %>" style="display: block;">
    <% var tourtag = tourtags[tourtagkey]; %>
    <h4>
        <%- tourtag.name %>
    </h4>
    <ul class="list-group">
    <% _.each(tourtag.tours, function(tour) { %>
        <li class="list-group-item">
            <a href="/tours/<%- tour.id %>" class="tourItem" data-tour.id=<%- tour.id %>>
                <%- tour.name || tour.id %>
            </a>
             - <%- tour.attributes.description || \"No description given.\" %>
             <% _.each(tour.attributes.tags, function(tag) { %>
                <span class="label label-primary sm-label-pad">
                    <%- tag.charAt(0).toUpperCase() + tag.slice(1) %>
                </span>
             <% }); %>
        </li>
    <% }); %>
    </ul>
</div>
<% }); %>`;

var tour_opts = {
    storage: window.sessionStorage,
    onEnd: function() {
        sessionStorage.removeItem("activeGalaxyTour");
    },
    delay: 150, // Attempts to make it look natural
    orphan: true
};

var hooked_tour_from_data = data => {
    _.each(data.steps, step => {
        if (step.preclick) {
            step.onShow = () => {
                _.each(step.preclick, preclick => {
                    // TODO: click delay between clicks
                    $(preclick).click();
                });
            };
        }
        if (step.postclick) {
            step.onHide = () => {
                _.each(step.postclick, postclick => {
                    // TODO: click delay between clicks
                    $(postclick).click();
                });
            };
        }
        if (step.textinsert) {
            // Have to manually trigger a change here, for some
            // elements which have additional logic, like the
            // upload input box
            step.onShown = () => {
                $(step.element)
                    .val(step.textinsert)
                    .trigger("change");
            };
        }
    });
    return data;
};

var TourItem = Backbone.Model.extend({
    urlRoot: `${gxy_root}api/tours`
});

var Tours = Backbone.Collection.extend({
    url: `${gxy_root}api/tours`,
    model: TourItem
});

var giveTour = tour_id => {
    var url = `${gxy_root}api/tours/${tour_id}`;
    $.getJSON(url, data => {
        // Set hooks for additional click and data entry actions.
        var tourdata = hooked_tour_from_data(data);
        sessionStorage.setItem("activeGalaxyTour", JSON.stringify(data));
        // Store tour steps in sessionStorage to easily persist w/o hackery.
        var tour = new Tour(
            _.extend(
                {
                    steps: tourdata.steps
                },
                tour_opts
            )
        );
        // Always clean restart, since this is a new, explicit giveTour execution.
        tour.init();
        tour.goTo(0);
        tour.restart();
    });
};

var ToursView = Backbone.View.extend({
    title: "Tours",
    // initialize
    initialize: function() {
        var self = this;
        this.setElement("<div/>");
        this.model = new Tours();
        this.model.fetch({
            success: function() {
                self.render();
            },
            error: function() {
                // Do something.
                console.error("Failed to fetch tours.");
            }
        });
    },

    render: function() {
        var tpl = _.template(tourpage_template);

        var tourtags = {};
        _.each(this.model.models, tour => {
            if (tour.attributes.tags === null) {
                if (tourtags.Untagged === undefined) {
                    tourtags.Untagged = { name: "Untagged", tours: [] };
                }
                tourtags.Untagged.tours.push(tour);
            } else {
                _.each(tour.attributes.tags, tag => {
                    tag = tag.charAt(0).toUpperCase() + tag.slice(1);
                    if (tourtags[tag] === undefined) {
                        tourtags[tag] = { name: tag, tours: [] };
                    }
                    tourtags[tag].tours.push(tour);
                });
            }
        });
        var tourtagorder = Object.keys(tourtags).sort();

        this.$el
            .html(
                tpl({
                    tours: this.model.models,
                    tourtags: tourtags,
                    tourtagorder: tourtagorder
                })
            )
            .on("click", ".tourItem", function(e) {
                e.preventDefault();
                giveTour($(this).data("tour.id"));
            })
            .on("click", ".tag-selector-button", e => {
                var elem = $(e.target);
                var display = "block";
                var tag = elem.attr("tag-selector-button");

                elem.toggleClass("btn-primary");
                elem.toggleClass("btn-secondary");

                if (elem.hasClass("btn-secondary")) {
                    display = "none";
                }
                $(`div[tag='${tag}']`).css({ display: display });
            });
    }
});

export default {
    ToursView: ToursView,
    hooked_tour_from_data: hooked_tour_from_data,
    tour_opts: tour_opts,
    giveTour: giveTour
};
