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

    statusComparator: function(repoA, repoB){
      var name_A = repoA.get("status").toLowerCase();
      var name_B = repoB.get("status").toLowerCase();
      var state_order = [
        'error',
        'installing',
        'cloning',
        'setting tool versions',
        'installing repository dependencies',
        'installing tool dependencies',
        'loading proprietary datatypes',
        'new',
        'installed',
        'deactivated',
        'uninstalled'
      ]
      if (state_order.indexOf(name_A) > state_order.indexOf(name_B)) {
        return -1;
      }
      if (state_order.indexOf(name_A) < state_order.indexOf(name_B)) {
        return 1;
      }
      return 0;
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
          this.comparator = this.statusComparator;
          break;
        case 'version':
          this.comparator = 'update';
          break;
      }
    }

  });

return {
    Repo: Repo,
    Repos: Repos
};

});
