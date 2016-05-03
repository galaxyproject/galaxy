define([], function() {

  var Repo = Backbone.Model.extend({
    urlRoot: Galaxy.root + 'api/admin/repos'
  });

  var Repos = Backbone.Collection.extend({
    url: Galaxy.root + 'api/admin/repos',

    model: Repo,

    dateComparator: function(repoA, repoB){
      var date_A = new Date(repoA.get("create_time").date);
      var date_B = new Date(repoB.get("create_time").date);
      if (date_A > date_B) {
        return -1;
      }
      if (date_B > date_A) {
        return 1;
      }
      return 0; // equal
    },

    switchComparator: function(comparator_name){
      switch (comparator_name){
        case 'date':
          this.comparator = this.dateComparator;
          break;
        case 'name':
          this.comparator = this.nameComparator;
          break;
      }
    }

  });

return {
    Repo: Repo,
    Repos: Repos
};

});
