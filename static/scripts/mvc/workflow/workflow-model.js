define("mvc/workflow/workflow-model", ["exports", "mvc/base-mvc"], function(exports, _baseMvc) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /* global Backbone */
    // workflow model

    var logNamespace = "workflow";
    //==============================================================================
    /** @class model for a single workflow.
     *  @name WorkflowItem
     *  @augments Backbone.Model
     */
    var WorkflowItem = Backbone.Model.extend(_baseMvc2.default.LoggableMixin).extend({
        _logNamespace: logNamespace,

        urlRoot: Galaxy.root + "api/workflows",

        toJSON: function toJSON() {
            // need to overwrite this as endpoint expects the 'workflow' key in payload
            return {
                workflow: this.attributes
            };
        }
    });

    //==============================================================================
    /** @class collection for workflows.
     *  @name WorkflowCollection
     *  @augments Backbone.Collection
     */
    var WorkflowCollection = Backbone.Collection.extend({
        model: WorkflowItem,
        url: Galaxy.root + "api/workflows"
    });

    //==============================================================================

    exports.default = {
        WorkflowItem: WorkflowItem,
        WorkflowCollection: WorkflowCollection
    };
});
//# sourceMappingURL=../../../maps/mvc/workflow/workflow-model.js.map
