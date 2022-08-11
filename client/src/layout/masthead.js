import { WindowManager } from "layout/window-manager";
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
        if (!Galaxy.frame) {
            Galaxy.frame = new WindowManager();
        }
        this.windowManager = Galaxy.frame;
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
