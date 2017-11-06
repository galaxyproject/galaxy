import baseMVC from "mvc/base-mvc";
/* global Backbone */
// workflow model

var logNamespace = "workflow";
//==============================================================================
/** @class model for a single workflow.
 *  @name WorkflowItem
 *  @augments Backbone.Model
 */
var WorkflowItem = Backbone.Model.extend(baseMVC.LoggableMixin).extend({
    _logNamespace: logNamespace,

    urlRoot: `${Galaxy.root}api/workflows`,

    toJSON: function() {
        // need to overwrite this as endpoint expects the 'workflow' key in payload
        return { workflow: this.attributes };
    }
});

//==============================================================================
/** @class collection for workflows.
 *  @name WorkflowCollection
 *  @augments Backbone.Collection
 */
var WorkflowCollection = Backbone.Collection.extend({
    model: WorkflowItem,
    url: `${Galaxy.root}api/workflows`
});

//==============================================================================

export default {
    WorkflowItem: WorkflowItem,
    WorkflowCollection: WorkflowCollection
};
