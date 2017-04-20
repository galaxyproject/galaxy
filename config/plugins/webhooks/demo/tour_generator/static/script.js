$(document).ready(function() {
    var ToolForm = window.toolform;

    window.TourGenerator = Backbone.View.extend({
        initialize: function(options) {
            var me = this;
            this.toolId = options.toolId;

            // Add attribute 'tour_id' to the execution button
            $('#execute').attr('tour_id', 'execute');

            Toastr.info('Tour generation will take some time.');
            $.getJSON('/api/webhooks/tour_generator/get_data/', {
                tool_id: this.toolId
            }, function(obj) {
                if (obj.success) {
                    $('#history-refresh-button').click(); // Refresh history panel

                    // Add a delay because of the history panel refreshing
                    setTimeout(function() {
                        var datasets = [],
                            numUploadedDatasets = 0;

                        _.each(obj.data.hids, function(hid) {
                            var dataset = Galaxy.currHistoryPanel.collection.where({
                                hid: hid
                            })[0];
                            if (dataset) datasets.push(dataset);
                        });

                        if (datasets.length === obj.data.hids.length) {
                            _.each(datasets, function(dataset) {
                                dataset.on('change:state', function(model) {
                                    if (model.get('state') === 'ok') numUploadedDatasets++;
                                    // Make sure that all test datasets have been successfully uploaded
                                    if (numUploadedDatasets === datasets.length) me._main(obj.data);
                                });
                            });
                        } else {
                            Toastr.error('Some of the test datasets cannot be found in the history.');
                        }
                    }, 500);
                } else {
                    Toastr.error(obj.error);
                    console.error('Tour Generator: ' + obj.error);
                    console.error(obj);
                }
            });
        },

        _main: function(data) {
            var tool = Galaxy.toolPanel.get('tools').get({
                id: this.toolId
            });

            // Create a tool form
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
});
