/**
 * Makes localization directives and filters available
 */

import { localize } from "utils/localization";

const newlineMatch = /\r?\n|\r/g;
const doublespaces = /\s\s+/g;

function localizeDirective(localize) {
    return {
        // TODO consider using a different hook if we need dynamic updates in content translation
        bind(el, binding, vnode) {
            el.childNodes.forEach((node) => {
                const standardizedContent = node.textContent
                    .replace(newlineMatch, " ")
                    .replace(doublespaces, " ")
                    .trim();
                node.textContent = localize(standardizedContent);
            });
        },
    };
}

export const localizationPlugin = {
    install(Vue, localize = localize) {
        Vue.directive("localize", localizeDirective(localize));
    },
};
