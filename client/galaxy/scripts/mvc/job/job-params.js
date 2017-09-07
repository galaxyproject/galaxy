/** Workflow view */
define( [ 'utils/utils' ], function( Utils ) {

    /** Build messages after user action */
    function build_messages( self ) {
        var $el_message = self.$el.find( '.response-message' ),
            status = Utils.getQueryString( 'status' ),
            message = Utils.getQueryString( 'message' );

        if( message && message !== "" ) {
            $el_message.addClass( status + 'message' );
            $el_message.html( '<p>' + _.escape( message ) + '</p>' );
        }
        else {
            $el_message.html("");
        }
    }

    /** View of the main workflow list page */
    var View = Backbone.View.extend({

        initialize: function( options ) {
            var self = this;
            this.options = options;
            this.setElement( '<div/>' );
            this.render();
        },

        render: function() {
            console.log('HI');
            var self = this;
            self.$el.empty().append( '<h1>Testing</h1>' );
            //var self = this,
                //min_query_length = 3;
            //$.getJSON( Galaxy.root + 'api/workflows/', function( workflows ) {
                //var $el_workflow = null;
                //// Add workflow header
                //// Add user actions message if any
                //build_messages( self );
                //$el_workflow = self.$el.find( '.user-workflows' );
                //// Add the actions buttons
                //$el_workflow.append( self._templateActionButtons() );
                //if( workflows.length > 0) {
                    //$el_workflow.append( self._templateWorkflowTable( self, workflows) );
                    //self.adjust_actiondropdown( $el_workflow );
                    //// Register delete and run workflow events
                    //_.each( workflows, function( wf ) {
                        //self.confirm_delete( self, wf );
                    //});
                    //// Register search workflow event
                    //self.search_workflow( self, self.$el.find( '.search-wf' ), self.$el.find( '.workflow-search tr' ), min_query_length );
                //}
                //else {
                    //$el_workflow.append( self._templateNoWorkflow() );
                //}
            //});
        }
    });

    return {
        View  : View
    };
});
