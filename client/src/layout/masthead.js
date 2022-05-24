import $ from "jquery";
import { WindowManager } from "layout/window-manager";
import QuotaMeter from "mvc/user/user-quotameter";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import Masthead from "../components/Masthead/Masthead";
import { mountVueComponent } from "../utils/mountVueComponent";

export class MastheadState {
    // Used to be a Backbone View - not pretty but keep all window wide listeners,
    // global state, etc... related to the Masthead here to keep the VueJS component
    // more isolated, testable, etc.. (clean)

    constructor(Galaxy = null) {
        Galaxy = Galaxy || getGalaxyInstance();
        Galaxy.frame = this.windowManager = new WindowManager();

        // set up the quota meter (And fetch the current user data from trans)
        // add quota meter to masthead
        Galaxy.quotaMeter = this.quotaMeter = new QuotaMeter.UserQuotaMeter({
            model: Galaxy.user,
            quotaUrl: Galaxy.config.quota_url,
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
                const text = this.windowManager.beforeUnload();
                if (text) {
                    return text;
                }
            });
    }
}

function staticUrlToPrefixed(appRoot, url) {
    return url?.startsWith("/") ? `${appRoot}${url.substring(1)}` : url;
}

export function mountMasthead(el, options, mastheadState) {
    const appRoot = getAppRoot();
    return mountVueComponent(Masthead)(
        {
            el: el,
            mastheadState: mastheadState,
            displayGalaxyBrand: options.display_galaxy_brand,
            brand: options.brand,
            brandLink: staticUrlToPrefixed(appRoot, options.logo_url),
            brandImage: staticUrlToPrefixed(appRoot, options.logo_src),
            brandImageSecondary: staticUrlToPrefixed(appRoot, options.logo_src_secondary),
            menuOptions: options,
        },
        el
    );
}
