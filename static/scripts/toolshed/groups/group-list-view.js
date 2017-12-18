define("toolshed/groups/group-list-view", ["exports", "libs/toastr", "toolshed/groups/group-model", "toolshed/groups/group-listrow-view"], function(exports, _toastr, _groupModel, _groupListrowView) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var mod_toastr = _interopRequireWildcard(_toastr);

    var _groupModel2 = _interopRequireDefault(_groupModel);

    var _groupListrowView2 = _interopRequireDefault(_groupListrowView);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    function _interopRequireWildcard(obj) {
        if (obj && obj.__esModule) {
            return obj;
        } else {
            var newObj = {};

            if (obj != null) {
                for (var key in obj) {
                    if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key];
                }
            }

            newObj.default = obj;
            return newObj;
        }
    }

    var GroupListView = Backbone.View.extend({
        el: "#groups_element",
        defaults: {},

        /**
         * Initialize and fetch the groups from server.
         * Async render afterwards.
         * @param  {object} options an object with options
         */
        initialize: function initialize(options) {
            this.options = _.defaults(this.options || {}, this.defaults, options);
            var that = this;
            window.globalTS.groups.collection = new _groupModel2.default.Groups();
            window.globalTS.groups.collection.fetch({
                success: function success(model) {
                    console.log("received data: ");
                    console.log(model);
                    that.render();
                },
                error: function error(model, response) {
                    if (typeof response.responseJSON !== "undefined") {
                        mod_toastr.error(response.responseJSON.err_msg);
                    } else {
                        mod_toastr.error("An error occurred.");
                    }
                }
            });
        },

        fetch: function fetch() {},

        /**
         * Render the groups table from the object's own collection.
         */
        render: function render(options) {
            this.options = _.extend(this.options, options);
            $(".tooltip").hide();
            var template = this.templateGroupsList();
            this.$el.html(template({
                length: window.globalTS.groups.collection.models.length
            }));
            this.renderRows(window.globalTS.groups.collection.models);
            $("#center [data-toggle]").tooltip();
            $("#center").css("overflow", "auto");
        },

        /**
         * Render all given models as rows in the groups list
         * @param  {array} groups_to_render array of group models to render
         */
        renderRows: function renderRows(groups_to_render) {
            for (var i = 0; i < groups_to_render.length; i++) {
                var group = groups_to_render[i];
                this.renderOne({
                    group: group
                });
            }
        },

        /**
         * Create a view for the given model and add it to the groups view.
         * @param {Group} model of the view that will be rendered
         */
        renderOne: function renderOne(options) {
            var rowView = new _groupListrowView2.default.GroupListRowView(options);
            this.$el.find("#group_list_body").append(rowView.el);
        },

        /**
         * Table heading was clicked, update sorting preferences and re-render.
         * @return {[type]} [description]
         */
        // sort_clicked : function(){
        //     if (Galaxy.libraries.preferences.get('sort_order') === 'asc'){
        //         Galaxy.libraries.preferences.set({'sort_order': 'desc'});
        //     } else {
        //         Galaxy.libraries.preferences.set({'sort_order': 'asc'});
        //     }
        //     this.render();
        // },

        /**
         * Sort the underlying collection according to the parameters received.
         * Currently supports only sorting by name.
         */
        // sortLibraries: function(){
        //     if (Galaxy.libraries.preferences.get('sort_by') === 'name'){
        //         if (Galaxy.libraries.preferences.get('sort_order') === 'asc'){
        //             this.collection.sortByNameAsc();
        //         } else if (Galaxy.libraries.preferences.get('sort_order') === 'desc'){
        //             this.collection.sortByNameDesc();
        //         }
        //     }
        // },

        // MMMMMMMMMMMMMMMMMM
        // === TEMPLATES ====
        // MMMMMMMMMMMMMMMMMM

        templateGroupsList: function templateGroupsList() {
            var tmpl_array = [];

            tmpl_array.push('<div id="groups">');
            tmpl_array.push("</div>");
            tmpl_array.push('<div class="groups_container table-responsive">');
            tmpl_array.push("<% if(length === 0) { %>");
            tmpl_array.push("<div>There are no groups yet.</div>");
            tmpl_array.push("<% } else{ %>");
            tmpl_array.push('<table class="grid table table-condensed">');
            tmpl_array.push("   <thead>");
            tmpl_array.push("     <th>Name</th>");
            // tmpl_array.push('     <th style="width:22%;">description</th>');
            tmpl_array.push("     <th>Members</th> ");
            tmpl_array.push("     <th>Repositories</th>");
            tmpl_array.push("   </thead>");
            tmpl_array.push('   <tbody id="group_list_body">');
            // group item views will attach here
            tmpl_array.push("   </tbody>");
            tmpl_array.push("</table>");
            tmpl_array.push("<% }%>");
            tmpl_array.push("</div>");

            return _.template(tmpl_array.join(""));
        }
    });

    exports.default = {
        GroupListView: GroupListView
    };
});
//# sourceMappingURL=../../../maps/toolshed/groups/group-list-view.js.map
