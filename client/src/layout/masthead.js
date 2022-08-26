import { WindowManager } from "layout/window-manager";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import Masthead from "../components/Masthead/Masthead";
import { mountVueComponent } from "../utils/mountVueComponent";
import Vue from "vue";

export const MASTHEAD_TAB_ID = Object.freeze({
    SHARED: "shared",
    ADMIN: "admin",
    HELP: "help",
    USER: "user",
    ANALYSIS: "analysis",
    WORKFLOW: "workflow",
    VISUALIZATION: "visualization",
});

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

function buildReactiveMastheadOptions(Galaxy = null, config = null) {
    Galaxy = Galaxy || getGalaxyInstance();
    config = config || Galaxy.config;
    const props = {
        defaultEnableAdmin: {
            default: Galaxy.user.get("is_admin"),
        },
        defaultEnableInteractiveTools: {
            default: config.interactivetools_enable,
        },
        defaultEnableVisualizations: {
            default: config.visualizations_visible,
        },
    };
    const data = {
        enableAdmin: props.defaultEnableAdmin,
        enableInteractiveTools: props.defaultEnableInteractiveTools,
        enableVisualizations: props.defaultEnableVisualizations,
        activeTab: null,
    };
    const methods = {
        reset() {
            this.enableAdmin = this.defaultEnableAdmin;
            this.enableInteractiveTools = this.defaultEnableInteractiveTools;
            this.enableVisualizations = this.defaultEnableVisualizations;
            this.activeTab = null;
        },
    };
    const vm = new Vue({ props, methods, data });
    return vm;
}

export function mountMasthead(el, Galaxy, config, mastheadState) {
    const appRoot = getAppRoot();
    const mastheadOptions = buildReactiveMastheadOptions(Galaxy, config);
    return mountVueComponent(Masthead)(
        {
            el: el,
            mastheadState: mastheadState,
            displayGalaxyBrand: config.display_galaxy_brand,
            brand: config.brand,
            brandLink: staticUrlToPrefixed(appRoot, config.logo_url),
            brandImage: staticUrlToPrefixed(appRoot, config.logo_src),
            brandImageSecondary: staticUrlToPrefixed(appRoot, config.logo_src_secondary),
            config: config,
            mastheadOptions: mastheadOptions,
        },
        el
    );
}
