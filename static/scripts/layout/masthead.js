define("layout/masthead", ["exports", "utils/utils", "layout/menu", "layout/scratchbook", "mvc/user/user-quotameter"], function(exports, _utils, _menu, _scratchbook, _userQuotameter) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    var _menu2 = _interopRequireDefault(_menu);

    var _scratchbook2 = _interopRequireDefault(_scratchbook);

    var _userQuotameter2 = _interopRequireDefault(_userQuotameter);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /** Masthead **/
    var View = Backbone.View.extend({
        initialize: function initialize(options) {
            var self = this;
            this.options = options;
            this.setElement(this._template());
            this.$navbarBrandLink = this.$(".navbar-brand-link");
            this.$navbarBrandImage = this.$(".navbar-brand-image");
            this.$navbarBrandTitle = this.$(".navbar-brand-title");
            this.$navbarTabs = this.$(".navbar-tabs");
            this.$quoteMeter = this.$(".quota-meter-container");

            // build tabs
            this.collection = new _menu2.default.Collection();
            this.collection.on("add", function(model) {
                self.$navbarTabs.append(new _menu2.default.Tab({
                    model: model
                }).render().$el);
            }).on("reset", function() {
                self.$navbarTabs.empty();
            }).on("dispatch", function(callback) {
                self.collection.each(function(m) {
                    callback(m);
                });
            }).fetch(this.options);

            // scratchbook
            Galaxy.frame = this.frame = new _scratchbook2.default({
                collection: this.collection
            });

            // set up the quota meter (And fetch the current user data from trans)
            // add quota meter to masthead
            Galaxy.quotaMeter = this.quotaMeter = new _userQuotameter2.default.UserQuotaMeter({
                model: Galaxy.user,
                el: this.$quoteMeter
            });

            // loop through beforeunload functions if the user attempts to unload the page
            $(window).on("click", function(e) {
                var $download_link = $(e.target).closest("a[download]");
                if ($download_link.length == 1) {
                    if ($("iframe[id=download]").length === 0) {
                        $("body").append($("<iframe/>").attr("id", "download").hide());
                    }
                    $("iframe[id=download]").attr("src", $download_link.attr("href"));
                    e.preventDefault();
                }
            }).on("beforeunload", function() {
                var text = "";
                self.collection.each(function(model) {
                    var q = model.get("onbeforeunload") && model.get("onbeforeunload")();
                    q && (text += q + " ");
                });
                if (text !== "") {
                    return text;
                }
            });
        },

        render: function render() {
            this.$navbarBrandTitle.html("Galaxy " + (this.options.brand && "/ " + this.options.brand || ""));
            this.$navbarBrandLink.attr("href", this.options.logo_url);
            this.$navbarBrandImage.attr("src", this.options.logo_src);
            this.quotaMeter.render();
            return this;
        },

        /** body template */
        _template: function _template() {
            return '<div id="masthead" class="navbar navbar-fixed-top navbar-inverse">' + '<div class="navbar-header">' + '<div class="navbar-tabs"/>' + "</div>" + '<div class="navbar-brand">' + '<a class="navbar-brand-link">' + '<img class="navbar-brand-image"/>' + '<span class="navbar-brand-title"/>' + "</a>" + "</div>" + '<div class="quota-meter-container"/>' + '<div class="navbar-icons"/>' + "</div>";
        }
    });

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../maps/layout/masthead.js.map
