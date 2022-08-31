import Masthead from "../components/Masthead/Masthead";
import { mountVueComponent } from "../utils/mountVueComponent";
import { fetchMenu } from "entry/analysis/menu";
import { WindowManager } from "layout/window-manager";
import { getGalaxyInstance } from "app";

export function mountMasthead(el, options) {
    const windowManager = new WindowManager(options);
    const Galaxy = getGalaxyInstance();
    Galaxy.frame = windowManager;
    return mountVueComponent(Masthead)(
        {
            el: el,
            displayGalaxyBrand: options.display_galaxy_brand,
            baseTabs: fetchMenu(options),
            brand: options.brand,
            brandLink: options.logo_url,
            brandImage: options.logo_src,
            brandImageSecondary: options.logo_src_secondary,
            windowTab: windowManager.getTab(),
        },
        el
    );
}
