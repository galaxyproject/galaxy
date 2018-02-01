$(document).ready(function() {
    require(['libs/toastr', 'mvc/tours'], function(Toastr, Tours) {
        window.TourGenerator = Backbone.View.extend({
            initialize: function(options) {
                var me = this;
                me.toolId = options.toolId;
                me.toolVersion = options.toolVersion;

                // Add attribute 'tour_id' to the execution button
                $('#execute').attr('tour_id', 'execute');

                Toastr.info('Tour generation might take some time.');
                $.getJSON('/api/webhooks/tour_generator/data/', {
                    tool_id: me.toolId,
                    tool_version: me.toolVersion
                }, function(obj) {
                    if (obj.success) {
                        if (obj.data.useDatasets) {
                            Galaxy.currHistoryPanel.refreshContents();  // Refresh history panel

                            // Add a delay because of the history panel refreshing
                            setTimeout(function () {
                                var datasets = [],
                                    numUploadedDatasets = 0;

                                _.each(obj.data.hids, function (hid) {
                                    var dataset = Galaxy.currHistoryPanel.collection.where({
                                        hid: hid
                                    })[0];
                                    if (dataset) datasets.push(dataset);
                                });

                                if (datasets.length === obj.data.hids.length) {
                                    _.each(datasets, function (dataset) {
                                        if (dataset.get('state') === 'ok') {
                                            numUploadedDatasets++;
                                        } else {
                                            dataset.on('change:state', function (model) {
                                                if (model.get('state') === 'ok') numUploadedDatasets++;
                                                // Make sure that all test datasets have been successfully uploaded
                                                if (numUploadedDatasets === datasets.length) me._generateTour(obj.data.tour);
                                            });
                                        }
                                    });
                                } else {
                                    Toastr.warning('Cannot generate a tour.');
                                    console.error('Some of the test datasets cannot be found in the history.');
                                }
                            }, 1500);
                        } else {
                            me._generateTour(obj.data.tour);
                        }
                    } else {
                        Toastr.warning('Cannot generate a tour.');
                        console.error('Tour Generator: ' + obj.error);
                    }
                });
            },

            _generateTour: function(data) {
                var tour = Tours.giveTourWithData(data);
                // Force ending the tour when pressing the Execute button
                $('#execute').on('mousedown', function() {
                    if (tour) {
                        tour.end();
                    }
                });
            }
        });
    });
});
