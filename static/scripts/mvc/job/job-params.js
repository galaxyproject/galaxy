define("mvc/job/job-params", ["exports", "utils/utils"], function(exports, _utils) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /** Build messages after user action */
    function build_messages(self) {
        var $el_message = self.$el.find(".response-message");
        var status = _utils2.default.getQueryString("status");
        var message = _utils2.default.getQueryString("message");

        if (message && message !== "") {
            $el_message.addClass(status + "message");
            $el_message.html("<p>" + _.escape(message) + "</p>");
        } else {
            $el_message.html("");
        }
    }

    /** View of the main workflow list page */
    /** Workflow view */
    var View = Backbone.View.extend({
        initialize: function initialize(options) {
            var self = this;
            this.options = options;
            this.setElement("<div/>");
            this.render();
        },

        render: function render() {
            console.log("HI");
            var self = this;
            self.$el.empty().append("<h1>Testing</h1>");
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

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/job/job-params.js.map
