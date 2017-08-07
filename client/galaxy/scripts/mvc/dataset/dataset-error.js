define( [ 'utils/utils', 'mvc/ui/ui-misc', 'mvc/form/form-view' ], function( Utils, Ui, Form ) {

    /** Dataset edit attributes view */
    var View = Backbone.View.extend({
        initialize: function() {
            this.setElement( '<div/>' );
            this.model = new Backbone.Model( { 'dataset_id': Galaxy.params.dataset_id } );
            this.render();
        },

        // Fetch data for the selected dataset and
        render: function() {
            var data_url = Galaxy.root + 'api/datasets/' + this.model.get( 'dataset_id' ),
                self = this;

            Utils.get({
                url     : data_url,
                success : function( data_response ) {
                    var job_url = Galaxy.root + 'api/jobs/' + data_response.creating_job + '?full=True';
                    Utils.get({
                        url     : job_url,
                        success : function( job_response ) {
                            var job_url = Galaxy.root + 'api/jobs/' + data_response.creating_job + '?full=True';
                            self.render_error_page( self, data_response, job_response );
                        },
                        error   : function( response ) {
                            var error_response = {
                                'status': 'error',
                                'message': 'Error occured while loading the job.',
                                'persistent': true,
                                'cls': 'errormessage'
                            };
                            self.display_message( error_response, self.$( '.response-message' ) );
                        }
                    });
                },
                error   : function( response ) {
                    var error_response = {
                        'status': 'error',
                        'message': 'Error occured while loading the dataset.',
                        'persistent': true,
                        'cls': 'errormessage'
                    };
                    self.display_message( error_response, self.$( '.response-message' ) );
                }
            });
        },

        /** Render the view */
        render_error_page: function( self, data_response, job_response ) {
            self.$el.empty().append( self._templateHeader() );
            console.log(data_response, job_response);
            //self.display_message( message, self.$( '.response-message' ) );
            // Create all tabs
            //self.create_tabs( response, self.$( '.edit-attr' ) );
            self.$el.append('<p>An error occured while creating <b>' + data_response.name + '</b></p>');
            self.$el.append('<p>Tool execution generated the following messages:</p>');
            self.$el.append('<pre>' + job_response.stderr + '</pre>');
            self.$el.append('<h2>Report This Error</pre>');
            self.$el.append('<p>Usually the local Galaxy administrators regularly review errors that occur on the server. However, if you would like to provide additional information (such as what you were trying to do when the error occurred) and a contact e-mail address, we will be better able to investigate your problem and get back to you.</p>');
            self.$el.append(self._getBugFormTemplate());
        },

        /** Perform AJAX post call */
        call_ajax: function( self, data, tab_name ) {
            var post_url = Galaxy.root + 'dataset/edit';
            $.ajax({
                type: "PUT",
                url: post_url,
                data: data,
                success: function( response ) {
                    self.render_attribute_page( self, response );
                },
                error   : function( response ) {
                    var error_response = {
                        'status': 'error',
                        'message': 'Error occured while saving. Please fill all the required fields and try again.',
                        'persistent': true,
                        'cls': 'errormessage'
                    };
                    self.display_message( error_response, self.$( '.response-message' ) );
                }
            });
        },

        /** Display actions messages */
        display_message: function( response, $el ) {
            $el.empty().html( new Ui.Message( response ).$el );
        },

        /** Main template */
        _templateHeader: function() {
            return '<div class="page-container edit-attr">' +
                       '<div class="response-message"></div>' +
                       '<h2>Dataset Error</h2>' +
                   '</div>';
        },

        /** Convert tab template */
        _getBugFormTemplate: function( response ) {
            var self = this;
            var form = new Form({
                title  : 'Error Report',
                inputs : [
                    {
                        "help": "Your email address",
                        "options": [],
                        "type": "text",
                        "name": "email",
                        "label": "Your email"
                    },
                    {
                        "help": "Any additional comments you can provide regarding what you were doing at the time of the bug.",
                        "options": [],
                        "type": "text",
                        "name": "email",
                        "label": "Message"
                    }
                ],

                operations: {
                    'submit' : new Ui.ButtonIcon({
                        tooltip  : 'Submit the bug report.',
                        title    : 'Submit',
                        icon     : 'fa-bug',
                    })
                }
            });
            return form.$el;
        },

        /** Submit action */
        _submit: function( self, form, response, type ) {
            var form_data = form.data.create();
            form_data.dataset_id = response.dataset_id;
            switch( type ) {
                case "edit_attributes":
                    form_data.save = 'Save';
                    break;

                case "auto-detect":
                    form_data.detect = 'Auto-detect';
                    break;

                case "convert":
                    if ( form_data.target_type !== null && form_data.target_type ) {
                        form_data.dataset_id = response.dataset_id;
                        form_data.convert_data = 'Convert';
                    }
                    break;

                case "change":
                    form_data.change = 'Save';
                    break;

                case "permissions":
                    var post_data = {};
                    post_data.permissions = JSON.stringify( form_data );
                    post_data.update_roles_button = "Save";
                    post_data.dataset_id = response.dataset_id;
                    form_data = post_data;
                    break;
            }
            self.call_ajax( self, form_data );
        }
    });

    return {
        View  : View
    };
});
