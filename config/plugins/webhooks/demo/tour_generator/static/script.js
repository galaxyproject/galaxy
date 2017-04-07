$(document).ready(function() {
    var ToolForm = window.toolform,
        Utils = window.utils;

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
                    // me._renderForm(obj);

                    var tour = me._generateTour(obj.data);

                    // Clean tour run
                    tour.init();
                    tour.goTo(0);
                    tour.restart();
                } else {
                    console.error('Tour Generator: ' + obj.error);
                }
            });
        },

        // _renderForm: function(obj) {
        //     var me = this,
        //         tool = Galaxy.toolPanel.get('tools').get({
        //             id: this.toolId
        //         });

        //     // Method #1
        //     // var toolForm = Galaxy.page.center.prev.form;

        //     // Method #2
        //     var toolForm = new ToolForm.View({
        //         id: tool.get('id'),
        //         version: tool.get('version')
        //     });

        //     // Show form
        //     toolForm.deferred.execute(function() {
        //         Galaxy.app.display(toolForm);
        //     });

        //     // Update form model
        //     var form = toolForm.form;
        //     form.deferred.reset();
        //     form.deferred.execute(function(process) {
        //         me._updateModel(form, process);
        //     });
        // },

        // _updateModel: function(form, process) {
        //     var formData = form.data.create();

        //     var currentState = {
        //         tool_id: this.toolId,
        //         tool_version: '1.0.2',
        //         inputs: $.extend(true, {}, form.data.create())
        //     };
        //     form.wait(true);
        //     currentState.inputs.columnList = 'c3';

        //     Utils.request({
        //         url: Galaxy.root + 'api/tools/' + this.toolId + '/build',
        //         type: 'POST',
        //         data: currentState,
        //         success: function(newModel) {
        //             form.update(newModel['tool_model'] || newModel);
        //             form.options.update && form.options.update(newModel);
        //             form.wait(false);
        //             Galaxy.emit.debug('tool-form-base::_updateModel()', 'Received new model.', newModel);
        //             process.resolve();
        //         },
        //         error: function(response) {
        //             Galaxy.emit.debug('tool-form-base::_updateModel()', 'Refresh request failed.', response);
        //             process.reject();
        //         }
        //     });
        // },

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
