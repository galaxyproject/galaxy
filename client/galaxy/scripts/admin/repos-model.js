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

    nameComparator: function(repoA, repoB){
      var name_A = repoA.get("name").toLowerCase();
      var name_B = repoB.get("name").toLowerCase();
      if (name_A > name_B) {
        return -1;
      }
      if (name_B > name_A) {
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
        case 'owner':
          this.comparator = 'owner';
          break;
        case 'installation':
          this.comparator = 'status';
          break;
      }
    }

  });

return {
    Repo: Repo,
    Repos: Repos
};

});
