$(document).ready(function() {
    var ToolForm = window.toolform;

    var TourGenerator = Backbone.View.extend({
        initialize: function(options) {
            var me = this;
            this.toolId = options.toolId;

            // Add attribute 'tour_id' to the execution button
            $('#execute').attr('tour_id', 'execute');

            var url = '/api/webhooks/tour_generator/get_data/' + JSON.stringify({
                'tool_id': this.toolId
            });

            $.getJSON(url, function(obj) {
                if (obj.success) {
                    $('#history-refresh-button').click(); // Refresh history panel

                    // Create a tour only when the uploaded dataset is ready
                    setTimeout(function() {
                        var dataset = Galaxy.currHistoryPanel.collection.where({
                            hid: obj.data.hid
                        })[0];

                        if (dataset) {
                            dataset.on('change:state', function(model) {
                                if (model.get('state') === 'ok') {
                                    me._main(obj.data);
                                }
                            });
                        }
                    }, 500);
                } else {
                    console.error('Tour Generator: ' + obj.error);
                    console.error(obj);
                }
            });
        },

        _main: function(data) {
            var tool = Galaxy.toolPanel.get('tools').get({
                id: this.toolId
            });

            // Create tool form
            var toolForm = new ToolForm.View({
                id: tool.get('id'),
                version: tool.get('version')
            });

            // Show the form
            Galaxy.page.center.display(toolForm);

            // Generate and run the tour
            var tour = this._generateTour(data.tour);
            tour.init();
            tour.goTo(0);
            tour.restart();
        },

        _generateTour: function(data) {
            var tourData = Tours.hooked_tour_from_data(data);
            sessionStorage.setItem('activeGalaxyTour', JSON.stringify(data));
            return new Tour(_.extend({
                steps: tourData.steps
            }));
        }
    });

    window.TourGenerator = TourGenerator;
});
