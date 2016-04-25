define([], function() {

  var Repo = Backbone.Model.extend({
    urlRoot: Galaxy.root + 'api/admin/repos'
  });

  var Repos = Backbone.Collection.extend({
    url: Galaxy.root + 'api/admin/repos',
    model: Repo
  });

return {
    Repo: Repo,
    Repos: Repos
};

});
