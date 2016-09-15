define([
  "libs/toastr",
  "admin/repos-model",
  "utils/utils"
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
    'change .select-version': 'selectVersion',
  },

  // repo browsing object
  jstree: null,

  initialize: function( options ){
    this.options = _.defaults(this.options || {}, options, this.defaults);
    this.model = new mod_repos_model.Repo();
    this.listenTo(this.model, 'sync', this.render);
    this.fetchRepo(this.options.id);
  },

  render: function( options ){
    this.options = _.extend( this.options, options );
    var repo_detail_template = this.templateRepoDetail();
    this.$el.html(repo_detail_template({repo: this.model}));
    if ($('.select-version').length > 0){
      $('.select-version').val(this.model.get('id'));
    }
    this.bindEvents();
    this.$el.find('[data-toggle]').tooltip();
    $( "#center" ).css( 'overflow','auto' );
  },

  rePaint: function( options ){
    $('.repos_container').remove();
    this.fetchRepo( options.id );
    this.render( options );
    // $('#repo_collapse_browser').collapse('show');
  },

  bindEvents: function(){
    var that = this;
    $('#repo_collapse_browser').on('show.bs.collapse', function () {
      that.refreshRepoTree();
    });

  },

  fetchRepo: function( id ){
    this.model.url = this.model.urlRoot + '/' + id + '?all_versions=true';
    this.model.fetch({
      success: function(model, response, options){
      },
      error: function(model, response, options){
      }
    });
  },

  selectVersion: function( event ){
    var selected_id = $( event.currentTarget ).val();
    if ( this.model.id !== selected_id ){
      this.rePaint( { id: selected_id } );
    }
  },

  refreshRepoTree: function( options ){
    var that = this;
    this.options = _.extend( this.options, options );
    if ( $('#repo_jstree_browser').children().length === 0 ){
      this.renderJstree( options );
      $('#repo_jstree_browser').on("changed.jstree", function (e, data) {
        if (data.node.type === 'file'){
          that.previewFile(data.node)
        } else if (data.node.type === 'folder'){
          $('#repo_jstree_browser').jstree('toggle_node', data.node);
        }
      });
    } else{
    }
  },

  /**
   * Fetch the contents of repo directory on Galaxy
   * and render jstree component based on received
   * data.
   * @param  {[type]} options [description]
   */
  renderJstree: function( options ){
    var that = this;
    this.options = _.extend( this.options, options );
    this.jstree = new mod_repos_model.Jstree();
    this.jstree.url = this.jstree.urlRoot + this.id + '/files';
    this.jstree.fetch({
      success: function(model, response){
        // This is to prevent double jquery load. I think. Carl is magician.
        define( 'jquery', function(){ return jQuery; });
        // Now we need jstree, time to lazy load it.
        require([ 'libs/jquery/jstree' ], function(jstree){
          $('#repo_jstree_browser').jstree("destroy");
          $('#repo_jstree_browser').jstree({
            'core':{
              'data': model
            },
            'plugins': ['types', 'changed', 'wholerow'],
            'types': {
              "folder": {
                "icon": "jstree-folder"
              },
              "file": {
                "icon": "jstree-file"
              }
            },
          });
        });
      },
      error: function(model, response){
        if (typeof response.responseJSON !== "undefined"){
          if (response.responseJSON.err_code === 404001){
            mod_toastr.warning(response.responseJSON.err_msg);
          } else{
            mod_toastr.error(response.responseJSON.err_msg);
          }
        } else {
          mod_toastr.error('An error ocurred.');
        }
      }
    })
  },

  previewFile: function(node){
    $('.code-preview').html('loading...');
    this.fetchFile(node.li_attr.full_path, this.model.get('changeset_revision'));
  },

  fetchFile: function( path, repo_revision ){
    mod_utils.get({
      url     : this.model.urlRoot + '/' + this.model.id + '/fetch',
      data    : {'path': path, 'repo_revision': repo_revision},
      success : function(file_preview) {
        $('.code-preview').html(file_preview);
      },
      error   : function(response, xhr) {
        mod_toastr.error('Failed to fetch preview of the requested file.');
        Galaxy.emit.debug('admin-repos::fetchFile()', 'Fetch file preview request failed.', response);
      }
    });
  },

  templateRepoDetail: function(){
    return _.template([
      '<div class="repos_container">',
        '<div class="detail-toolbar">',
          '<a href="#repos">< back to installed repositories</a>',
          '<button>repair</button>',
          '<button>reset metadata</button>',
          '<button>update</button>',
          '<button>uninstall</button>',
          '<button>set tool versions</button>',
        '</div>',

        '<div class="repo_accord" role="tablist">',

          '<div class="card">',
            '<a role="button" data-toggle="collapse" data-parent=".repo_accord" href="#repo_collapse_1">',
              '<div class="card-header" role="tab" id="repo_section_1">',
                '<h5 class="card-title">',
                    'Repository Details',
                '</h5>',
              '</div>',
            '</a>',
            '<div id="repo_collapse_1" class="card-collapse collapse in" role="tabpanel">',
              '<div class="card-body">',
                '<table class="grid table table-condensed">',
                  '<tbody>',
                    '<tr>',
                      '<td style="width:33%;">Name</td>',
                      '<td><%- repo.get("name") %></td>',
                    '</tr>',
                    '<tr>',
                      '<td>Owner</td>',
                      '<td><%- repo.get("owner") %></td>',
                    '</tr>',
                    '<tr>',
                      '<td>Tool Shed</td>',
                      '<td><%- repo.get("tool_shed") %></td>',
                    '</tr>',
                    '<tr>',
                      '<td>Description</td>',
                      '<td><%- repo.get("description") %></td>',
                    '</tr>',
                    '<tr>',
                      '<td>Version</td>',
                      '<td>',
                        '<% if(repo.get("versions")) { %>',
                            '<select class="form-control select-version">',
                              '<% _.each(repo.get("versions"), function(version) { %>',
                                '<option value="<%- version.id %>"><%- version.ctx_rev %> (<%- version.changeset_revision %>)</option>',
                              '<% }) %>',
                            '</select>',
                            '<a href="<%- repo.get("revision_url") %>" target="_blank" data-toggle="tooltip" data-placement="right" title="new tab">',
                              'see this revision in Tool Shed',
                            '</a>',
                        '<% } else { %>',
                          '<a href="<%- repo.get("revision_url") %>" target="_blank" data-toggle="tooltip" data-placement="right" title="show in Tool Shed">',
                            '<%- repo.get("revision_url") %>',
                          '</a>',
                        '<% }%>',
                      '</td>',
                    '</tr>',
                  '</tbody>',
                '</table>',
              '</div>',
            '</div>',
          '</div>',

          '<div class="card">',
            '<a role="button" data-toggle="collapse" data-parent=".repo_accord" href="#repo_collapse_2">',
              '<div class="card-header" role="tab" id="repo_section_2">',
                '<h5 class="card-title">',
                    'Installation Details',
                '</h5>',
              '</div>',
            '</a>',
            '<div id="repo_collapse_2" class="card-collapse collapse in" role="tabpanel">',
              '<div class="card-body">',
                '<table class="grid table table-condensed">',
                  '<tbody>',
                    '<tr>',
                      '<td style="width: 33%;">Status</td>',
                      '<td>',
                        '<div class="celldiv status-<%- repo.get("status").toLowerCase().replace(/ /g,"-") %>">',
                          '<%- repo.get("status").toLowerCase() %>',
                          '<% if(repo.get("collapsed_repos")) { %>',
                            '<span data-toggle="tooltip" data-placement="top" title="multiple revisions detected" class="fa fa-compress icon-inline"/>',
                          '<% } %>',
                        '</div>',
                      '</td>',
                    '</tr>',
                    '<tr>',
                      '<td>Date Installed</td>',
                      '<td data-toggle="tooltip" data-placement="left" title="<%- repo.get("create_time").date %>" >',
                        '<%- repo.get("create_time").interval %>',
                      '</td>',
                    '</tr>',
                    '<tr>',
                      '<td>Location</td>',
                      '<td><%- repo.get("repo_location") %></td>',
                    '</tr>',
                    '<tr>',
                      '<td>ID</td>',
                      '<td><%- repo.get("id") %></td>',
                    '</tr>',
                  '</tbody>',
                '</table>',
              '</div>',
            '</div>',
          '</div>',

          '<div class="card">',
            '<a role="button" data-toggle="collapse" data-parent=".repo_accord" href="#repo_collapse_3">',
              '<div class="card-header" role="tab" id="repo_section_3">',
                '<h5 class="card-title">',
                    'Artifacts',
                '</h5>',
              '</div>',
            '</a>',
            '<div id="repo_collapse_3" class="card-collapse collapse" role="tabpanel">',
              '<div class="card-body">',
                'sdsd',
              '</div>',
            '</div>',
          '</div>',

          '<div class="card">',
            '<a role="button" data-toggle="collapse" data-parent=".repo_accord" href="#repo_collapse_4">',
              '<div class="card-header" role="tab" id="repo_section_4">',
                '<h5 class="card-title">',
                    'Dependency Resolver Details',
                '</h5>',
              '</div>',
            '</a>',
            '<div id="repo_collapse_4" class="card-collapse collapse" role="tabpanel">',
              '<div class="card-body">',
                'sdsd',
              '</div>',
            '</div>',
          '</div>',

          '<div class="card">',
            '<a role="button" data-toggle="collapse" data-parent=".repo_accord" href="#repo_collapse_5">',
              '<div class="card-header" role="tab" id="repo_section_5">',
                '<h5 class="card-title">',
                    'Dependencies',
                '</h5>',
              '</div>',
            '</a>',
            '<div id="repo_collapse_5" class="card-collapse collapse" role="tabpanel">',
              '<div class="card-body">',
                'sdsd',
              '</div>',
            '</div>',
          '</div>',

          '<div class="card">',
            '<a role="button" data-toggle="collapse" data-parent=".repo_accord" href="#repo_collapse_browser" class="repo-browser">',
              '<div class="card-header" role="tab" id="repo_section_6">',
                '<h5 class="card-title">',
                    'Browse files',
                '</h5>',
              '</div>',
            '</a>',
            '<div id="repo_collapse_browser" class="card-collapse collapse" role="tabpanel">',
              '<div class="card-body">',
                '<div>repository contents at <%- repo.get("changeset_revision") %></div>',

                // append jstree object here
                '<div id="repo_jstree_browser">',
                '</div>',

                // append file preview here
                '<div class="file-preview">',
                '<pre>',
                '<code class="code-preview">',
                '</code>',
                '</pre>',
                '</div>',

              '</div>',
            '</div>',
          '</div>',

        '</div>',
      '</div>',
    ].join(''));
  }

});

return {
    AdminReposDetailView: AdminReposDetailView
};

});
