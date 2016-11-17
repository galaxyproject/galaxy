define([
  "libs/toastr",
  ],
  function(
    mod_toastr
   ) {

var AdminReposRowView = Backbone.View.extend({

  events: {
    'click' : 'selectOne',
  },

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
    this.$el.find('[data-toggle]').tooltip();
    return this;
  },

  /**
   * Select the checkbox even if just the <td> is clicked
   * to improve usability. Also toggle the row color.
   * @param  event
   */
  selectOne: function (event) {
    var checkbox = '';
    var $row;
    var source;
    if (event.target.localName === 'input'){
        checkbox = event.target;
        $row = $(event.target.parentElement.parentElement);
        source = 'input';
    } else if (event.target.localName === 'td') {
        $row = $(event.target.parentElement);
        checkbox = $row.find(':checkbox')[0];
        source = 'td';
    } else if (event.target.localName === 'div') {
        $row = $(event.target.parentElement.parentElement);
        checkbox = $row.find(':checkbox')[0];
        source = 'div';
    }
    if (checkbox.checked){
        if (source === 'td' || source === 'div'){
            checkbox.checked = '';
            this.turnLight($row);
        } else if (source === 'input') {
            this.turnDark($row);
        }
    } else {
        if (source === 'td' || source === 'div'){
            checkbox.checked = 'selected';
            this.turnDark($row);
        } else if (source === 'input') {
            this.turnLight($row);
        }
      }
  },

  turnDark: function(){
    this.$el.removeClass('light').addClass('dark');
  },

  turnLight: function(){
    this.$el.removeClass('dark').addClass('light');
  },

  templateRepoRow: function(){
    return _.template([
    '<tr class="repo-row light" style="display:none; " data-id="<%- repo.get("id") %>">',
      // Checkbox column
      '<td style="text-align: center; " class="checkbox-cell">',
        '<input style="margin: 0;" type="checkbox">',
      '</td>',
      // Name column
      '<td>',
        '<% if(repo.get("name")) { %>',
          '<a href="#repos/<%- repo.get("id") %>"><%- repo.get("name") %></a>',
          '<% if(repo.get("collapsed_repos")) { %>',
            '<span data-toggle="tooltip" data-placement="top" title="multiple revisions detected" class="fa fa-compress icon-inline"/>',
          '<% } %>',
        '<% } %>',
      '</td>',
      // Info column
      '<td>',
        '<% if( repo.get("tool_shed").indexOf("toolshed.g2.bx.psu.edu") === -1 ) { %>',
          '<span data-toggle="tooltip" data-placement="top" title="from <%- repo.get("tool_shed") %>" class="fa fa-home icon-inline"/>',
        '<% } %>',
      '</td>',
      // Owner column
      '<td>',
        '<% if(repo.get("owner")) { %>',
          '<%- repo.get("owner") %>',
        '<% } %>',
      '</td>',
      // Installation column
      '<td class="centercell">',
        '<div class="status-<%- repo.get("status").toLowerCase().replace(/ /g,"-") %>">',
          '<%- repo.get("status").toLowerCase() %>',
          '<% if(repo.get("collapsed_repos")) { %>',
            '<span data-toggle="tooltip" data-placement="top" title="multiple revisions detected" class="fa fa-compress icon-inline"/>',
          '<% } %>',
        '</div>',
      '</td>',
      // Version column
      // '<% if(repo.get("status").toLowerCase() === "uninstalled") { %>',
      //   '<td class="centercell">',
      //     'N/A',
      //   '</td>',
      // '<% } else{%>',
        '<td class="centercell">',
          '<div class="update-<%- repo.get("update").toLowerCase().replace(/ /g,"-") %>">',
            '<%- repo.get("update") %>',
            '<% if(repo.get("collapsed_repos")) { %>',
              '<span data-toggle="tooltip" data-placement="top" title="multiple revisions detected" class="fa fa-compress icon-inline"/>',
            '<% } %>',
          '</div>',
        '</td>',
      // '<% } %>',
      // Date installed column
      '<% if(repo.get("create_time")) { %>',
        '<td data-toggle="tooltip" data-placement="top" title="<%- repo.get("create_time").date %>" >',
          '<%- repo.get("create_time").interval %>',
        '</td>',
      '<% } else { %>',
        '<td/>',
      '<% } %>',
    '</tr>'
    ].join(''));
  }

});

return {
    AdminReposRowView: AdminReposRowView
};

});
