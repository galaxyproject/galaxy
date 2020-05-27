import $ from "jquery";
import Backbone from "backbone";
import { fetchMenu } from "layout/menu";
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
        this.options = options;
        this._component = null;
        // build tabs
        this.collection = fetchMenu(options);

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
                const text = this.frame.beforeUnload();
                if(text) {
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
        const defaults = {
            visible: true,
            target: "_parent",
        };
        const tabs = this.collection.map((el) => {
            let asJson;
            if (el.toJSON instanceof Function) {
                asJson = el.toJSON();
            } else {
                asJson = el;
            }
            return Object.assign({}, defaults, asJson);
        });
        this._component = mountVueComponent(Masthead)(
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

    addItem(item) {
        this._component.addItem(item);
    },

    highlight(activeTab) {
        this._component.highlight(activeTab);
    },
});

export default {
    View: View,
};
