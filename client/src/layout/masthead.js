import Masthead from "../components/Masthead/Masthead";
import { mountVueComponent } from "../utils/mountVueComponent";
import { fetchMenu } from "entry/analysis/menu";
import { safePath } from "utils/redirect";

export function mountMasthead(el, options) {
    return mountVueComponent(Masthead)(
        {
            el: el,
            displayGalaxyBrand: options.display_galaxy_brand,
            baseTabs: fetchMenu(options),
            brand: options.brand,
            brandLink: safePath(options.logo_url),
            brandImage: safePath(options.logo_src),
            brandImageSecondary: safePath(options.logo_src_secondary),
        },
        el
    );
}
