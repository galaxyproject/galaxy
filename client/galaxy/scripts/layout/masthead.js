import $ from "jquery";
import Backbone from "backbone";
import Menu from "layout/menu";
import Scratchbook from "layout/scratchbook";
import QuotaMeter from "mvc/user/user-quotameter";
import { getGalaxyInstance } from "app";

import Masthead from "../components/Masthead.vue";
import { mountVueComponent } from "../utils/mountVueComponent";
import _ from "../libs/underscore";
import { getAppRoot } from "onload/loadConfig";

/** Masthead **/
const View = Backbone.View.extend({
    initialize: function(options) {
        const Galaxy = getGalaxyInstance();

        const self = this;
        this.options = options;

        // build tabs
        this.collection = new Menu.Collection();
        this.collection
            .on("dispatch", callback => {
                self.collection.each(m => {
                    callback(m);
                });
            })
            .fetch(this.options);

        // highlight initial active view
        this.highlight(options.active_view); // covered

        // scratchbook
        Galaxy.frame = this.frame = new Scratchbook({
            collection: this.collection
        });

        // set up the quota meter (And fetch the current user data from trans)
        // add quota meter to masthead
        Galaxy.quotaMeter = this.quotaMeter = new QuotaMeter.UserQuotaMeter({
            model: Galaxy.user,
        });

        // loop through beforeunload functions if the user attempts to unload the page
        $(window)
            .on("click", e => {
                const $download_link = $(e.target).closest("a[download]");
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
                let text = "";
                self.collection.each(model => {
                    const q = model.get("onbeforeunload") && model.get("onbeforeunload")();
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
        const el = document.createElement("div");
        this.el.appendChild(el); // use this.el directly when feature parity is accomplished

        mountVueComponent(Masthead)(
            {
                // params
                brandTitle: `Galaxy ${(this.options.brand && `/ ${this.options.brand}`) || ""}`,
                brandLink: this.options.logo_url,
                brandImage: this.options.logo_src,

                quotaMeter: this.quotaMeter,
                activeTab: () => {
                    return this.activeView;
                },
                tabs: _.map(this.collection.models, el => {
                    return el.toJSON();
                }),

                frames: this.frame.getFrames(),

                appRoot: getAppRoot(),
                Galaxy: getGalaxyInstance()
            },
            el
        );
        return this;
    },

    highlight: function(id) {
        this.activeView = id;
        this.collection.forEach(function(model) {
            model.set("active", model.id == id);
        });
    },

    /** body template */
    _template: function() {
        return `
            <div>
                <nav id="masthead" class="navbar navbar-expand justify-content-center navbar-dark" role="navigation" aria-label="Main">
                    <a class="navbar-brand" aria-label="homepage">
                        <img alt="logo" class="navbar-brand-image"/>
                        <span class="navbar-brand-title"/>
                    </a>
                    <ul class="navbar-nav"/>
                    <div class="quota-meter-container"/>
                </nav>
            </div>`;
    }
});

export default {
    View: View
};
