import $ from "jquery";
import Backbone from "backbone";
import Menu from "layout/menu";
import Scratchbook from "layout/scratchbook";
import QuotaMeter from "mvc/user/user-quotameter";
import { getGalaxyInstance } from "app";
import Masthead from "../components/Masthead/Masthead";
import { mountVueComponent } from "../utils/mountVueComponent";
import { getAppRoot } from "onload/loadConfig";

/** Masthead **/
const View = Backbone.View.extend({
    initialize: function (options) {
        const Galaxy = getGalaxyInstance();
        const self = this;
        this.options = options;

        // build tabs
        this.collection = new Menu.Collection();
        this.collection
            .on("dispatch", (callback) => {
                self.collection.each((m) => {
                    callback(m);
                });
            })
            .fetch(this.options);

        // highlight initial active view
        this.highlight(options.active_view); // covered

        // scratchbook
        Galaxy.frame = this.frame = new Scratchbook({
            collection: this.collection,
        });

        // set up the quota meter (And fetch the current user data from trans)
        // add quota meter to masthead
        Galaxy.quotaMeter = this.quotaMeter = new QuotaMeter.UserQuotaMeter({
            model: Galaxy.user,
        });

        // loop through beforeunload functions if the user attempts to unload the page
        $(window)
            .on("click", (e) => {
                const $download_link = $(e.target).closest("a[download]");
                if ($download_link.length == 1) {
                    if ($("iframe[id=download]").length === 0) {
                        $("body").append($("<iframe/>").attr("id", "download").hide());
                    }
                    $("iframe[id=download]").attr("src", $download_link.attr("href"));
                    e.preventDefault();
                }
            })
            .on("beforeunload", () => {
                let text = "";
                self.collection.each((model) => {
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

    render: function () {
        const el = document.createElement("div");
        this.el.appendChild(el); // use this.el directly when feature parity is accomplished
        let brandTitle = this.options.display_galaxy_brand ? "Galaxy " : "";
        if (this.options.brand) {
            brandTitle += this.options.brand;
        }
        const tabs = this.collection.models.map((el) => {
            return el.toJSON();
        });
        mountVueComponent(Masthead)(
            {
                brandTitle: brandTitle,
                brandLink: this.options.logo_url,
                brandImage: this.options.logo_src,
                quotaMeter: this.quotaMeter,
                activeTab: this.activeView,
                tabs: tabs,
                frames: this.frame.getFrames(),
                appRoot: getAppRoot(),
                Galaxy: getGalaxyInstance(),
            },
            el
        );
        return this;
    },

    highlight: function (id) {
        this.activeView = id;
        this.collection.forEach(function (model) {
            model.set("active", model.id == id);
        });
    },
});

export default {
    View: View,
};
