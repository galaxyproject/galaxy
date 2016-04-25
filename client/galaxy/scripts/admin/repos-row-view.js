define([
  "libs/toastr",
  ],
  function(
    mod_toastr
   ) {

var AdminReposRowView = Backbone.View.extend({

  initialize: function(options){
    this.options = _.defaults( this.options || {}, options, this.defaults );
    this.render();
  },

  render: function(){
    // if (typeof repo === 'undefined'){
    //   repo = Galaxy.adminapp.adminReposListView.collection.get(this.options.repo.id);
    // }
    var repo_row_template = this.templateRepoRow();
    this.setElement(repo_row_template({repo: this.options.repo}));
    this.$el.show();
    return this;
  },

  templateRepoRow: function(){
    return _.template([
    '<tr class="repo-row" style="display:none;" data-id="<%- repo.get("id") %>">',
      '<td>',
        '<%- repo.get("name") %>',
      '</td>',
      '<td>',
        '<%- repo.get("owner") %>',
      '</td>',
      '<td>',
        '<%- repo.get("status") %>',
      '</td>',
      '<td>',
        'unknown',
      '</td>',
      '<td>',
        'unknown',
      '</td>',
      '<td>',
        '<%- repo.get("create_time") %>',
      '</td>',
    '</tr>'
    ].join(''));
  }

});

return {
    AdminReposRowView: AdminReposRowView
};

});
