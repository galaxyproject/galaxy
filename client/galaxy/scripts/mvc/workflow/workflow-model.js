import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import baseMVC from "mvc/base-mvc";

// workflow model

var logNamespace = "workflow";
//==============================================================================
/** @class model for a single workflow.
 *  @name WorkflowItem
 *  @augments Backbone.Model
 */
var WorkflowItem = Backbone.Model.extend(baseMVC.LoggableMixin).extend({
    _logNamespace: logNamespace,

    urlRoot: `${getAppRoot()}api/workflows`,

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
    url: `${getAppRoot()}api/workflows`
});

//==============================================================================

export default {
    WorkflowItem: WorkflowItem,
    WorkflowCollection: WorkflowCollection
};
