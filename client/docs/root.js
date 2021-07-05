/**
 * Component root for rendering inside the styleguide, injects vuex store and other common elements
 * into each component example section.
 */

import store from "../src/store";

export default (previewComponent) => {
    return {
        store,
        render(h) {
            return h(previewComponent);
        },
    };
};
