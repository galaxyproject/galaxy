define([], function() {

// ============================================================================
// TS GROUP RELATED MODELS

    var Group = Backbone.Model.extend({
      urlRoot: '/api/groups',
    });

    var Groups = Backbone.Collection.extend({
      url: '/api/groups',

      model: Group,

    });

return {
    Group: Group,
    Groups: Groups
};

});
