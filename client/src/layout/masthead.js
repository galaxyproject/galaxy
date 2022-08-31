import Masthead from "components/Masthead/Masthead";
import { mountVueComponent } from "utils/mountVueComponent";
import { fetchMenu } from "entry/analysis/menu";
import { safePath } from "utils/redirect";

export function mountMasthead(el, options) {
    const mounted = mountVueComponent(Masthead)(
        {
            el: el,
            displayGalaxyBrand: options.display_galaxy_brand,
            tabs: fetchMenu(options),
            brand: options.brand,
            logoUrl: options.logo_url,
            logoSrc: options.logo_src,
            logoSrcSecondary: options.logo_src_secondary,
        },
        el
    );
    mounted.$on("open-url", (options) => {
        window.location = safePath(options.url);
    });
    return mounted;
}
