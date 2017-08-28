define([
    "mvc/base-mvc",
], function( baseMVC ){
/* global Backbone */
// workflow model

var logNamespace = 'workflow';
//==============================================================================
/** @class model for tool citations.
 *  @name Citation
 *  @augments Backbone.Model
 */
var WorkflowItem = Backbone.Model.extend( baseMVC.LoggableMixin ).extend({
    _logNamespace : logNamespace,

    urlRoot: '/api/workflows',

    toJSON: function(){
    // need to overwrite this as endpoint expects the 'workflow' key in payload
    return {workflow : this.attributes};
    },

    download: function() {
        return $.getJSON(this.urlRoot + this.model.id + '/download')
    },

});

var WorkflowCollection = Backbone.Collection.extend({
    model: WorkflowItem,
    url: '/api/workflows',

    initialize: function () {
        this.fetch();
    }
  });

//==============================================================================

return {
    WorkflowItem: WorkflowItem,
    WorkflowCollection: WorkflowCollection,
};


});