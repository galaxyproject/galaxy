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
var WorkflowModel = Backbone.Model.extend( baseMVC.LoggableMixin ).extend({
    _logNamespace : logNamespace,

    defaults : {
        content: ''
    },

    initialize: function() {
        console.log("Initialize Workflow Model");
    },

    entryType: function() {
        return this.entry? this.entry.EntryType : undefined;
    },
    fields: function() {
        return this._fields;
    }
});


//==============================================================================

return WorkflowModel;


});