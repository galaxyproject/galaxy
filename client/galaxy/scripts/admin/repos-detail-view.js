define([
  "libs/toastr",
  "admin/repos-model",
  "utils/utils",
  ],
  function(
    mod_toastr,
    mod_repos_model,
    mod_utils
   ) {

var AdminReposDetailView = Backbone.View.extend({
  el: '#center',

  defaults: {
  },

  events: {
  },

  initialize: function( options ){
    this.options = _.defaults( this.options || {}, options, this.defaults );
    this.model =
    this.render();
  },

  render: function(options){
    this.options = _.extend( this.options, options );
    var repo_detail_template = this.templateRepoDetail();
    this.$el.html(repo_detail_template({}));
  },

  fetchRepo: function(){

  },

  templateRepoDetail: function(){
    return _.template([
      '<div>',
      'TRALALA',
      '</div>',
    ].join(''));
  }

});

return {
    AdminReposDetailView: AdminReposDetailView
};

});
