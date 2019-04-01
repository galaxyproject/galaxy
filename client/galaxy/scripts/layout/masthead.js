import $ from "jquery";
import Backbone from "backbone";
import Menu from "layout/menu";
import Scratchbook from "layout/scratchbook";
import QuotaMeter from "mvc/user/user-quotameter";
import { getGalaxyInstance } from "app";

/** Masthead **/
var View = Backbone.View.extend({
    initialize: function(options) {
        let Galaxy = getGalaxyInstance();

        var self = this;
        this.options = options;
        this.setElement(this._template());
        this.$navbarBrandLink = this.$(".navbar-brand");
        this.$navbarBrandImage = this.$(".navbar-brand-image");
        this.$navbarBrandTitle = this.$(".navbar-brand-title");
        this.$navbarTabs = this.$(".navbar-nav");
        this.$quoteMeter = this.$(".quota-meter-container");

        // build tabs
        this.collection = new Menu.Collection();
        this.collection
            .on("add", model => {
                self.$navbarTabs.append(new Menu.Tab({ model: model }).render().$el);
            })
            .on("reset", () => {
                self.$navbarTabs.empty();
            })
            .on("dispatch", callback => {
                self.collection.each(m => {
                    callback(m);
                });
            })
            .fetch(this.options);

        // highlight initial active view
        this.highlight(options.active_view);

        // scratchbook
        Galaxy.frame = this.frame = new Scratchbook({
            collection: this.collection
        });

        // set up the quota meter (And fetch the current user data from trans)
        // add quota meter to masthead
        Galaxy.quotaMeter = this.quotaMeter = new QuotaMeter.UserQuotaMeter({
            model: Galaxy.user,
            el: this.$quoteMeter
        });

        // loop through beforeunload functions if the user attempts to unload the page
        $(window)
            .on("click", e => {
                var $download_link = $(e.target).closest("a[download]");
                if ($download_link.length == 1) {
                    if ($("iframe[id=download]").length === 0) {
                        $("body").append(
                            $("<iframe/>")
                                .attr("id", "download")
                                .hide()
                        );
                    }
                    $("iframe[id=download]").attr("src", $download_link.attr("href"));
                    e.preventDefault();
                }
            })
            .on("beforeunload", () => {
                var text = "";
                self.collection.each(model => {
                    var q = model.get("onbeforeunload") && model.get("onbeforeunload")();
                    if (q) {
                        text += `${q} `;
                    }
                });
                if (text !== "") {
                    return text;
                }
            });
    },

    render: function() {
        this.$navbarBrandTitle.html(`Galaxy ${(this.options.brand && `/ ${this.options.brand}`) || ""}`);
        this.$navbarBrandLink.attr("href", this.options.logo_url);
        this.$navbarBrandImage.attr("src", this.options.logo_src);
        this.quotaMeter.render();
        return this;
    },

    highlight: function(id) {
        this.collection.forEach(function(model) {
            model.set("active", model.id == id);
        });
    },

    /** body template */
    _template: function() {
        return `
            <nav id="masthead" class="navbar navbar-expand justify-content-center navbar-dark">
                <a class="navbar-brand">
                    <img class="navbar-brand-image"/>
                    <span class="navbar-brand-title"/>
                </a>
                <ul class="navbar-nav"/>
                <div class="quota-meter-container"/>
            </nav>`;
    }
});

export default {
    View: View
};
