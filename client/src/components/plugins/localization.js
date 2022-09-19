/**
 * Makes localization directives and filters available
 */

import _l from "utils/localization";

const newlineMatch = /\r?\n|\r/g;
const doublespaces = /\s\s+/g;

function localizeDirective(l) {
    return {
        // TODO consider using a different hook if we need dynamic updates in content translation
        bind(el, binding, vnode) {
            el.childNodes.forEach((node) => {
                const standardizedContent = node.textContent
                    .replace(newlineMatch, " ")
                    .replace(doublespaces, " ")
                    .trim();
                node.textContent = l(standardizedContent);
            });
        },
    };
}

// adds localizeText mixin
function localizeMixin(l) {
    return {
        methods: {
            l: l,
            localize: l,
        },
    };
}

export const localizationPlugin = {
    install(Vue, l = _l) {
        Vue.filter("localize", l);
        Vue.filter("l", l);
        Vue.directive("localize", localizeDirective(l));
        Vue.mixin(localizeMixin(l));
    },
};
