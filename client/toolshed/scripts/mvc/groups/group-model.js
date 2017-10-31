define([], function() {

// ============================================================================
// TS GROUP RELATED MODELS

    var Group = Backbone.Model.extend({
      urlRoot: Galaxy.root + 'api/groups',
    });

    var Groups = Backbone.Collection.extend({
      url: Galaxy.root + 'api/groups',

      model: Group,

    });

return {
    Group: Group,
    Groups: Groups
};

});
