/**
 * Makes localization directives and filters available
 */

import _l from "utils/localization";

const newlineMatch = /\r?\n|\r/g;
const doublespaces = /\s\s+/g;

function localizeDirective(l) {
    return {
        // TODO consider using a different hook if we need dynamic updates in content translation
        beforeMount(el, binding, vnode) {
            el.childNodes.forEach((node) => {
                // trim for lookup, but put back whitespace after
                const leadingSpace = node.textContent.match(/^\s*/)[0];
                const trailingSpace = node.textContent.match(/\s*$/)[0];
                const standardizedContent = node.textContent
                    .replace(newlineMatch, " ")
                    .replace(doublespaces, " ")
                    .trim();
                node.textContent = leadingSpace + l(standardizedContent) + trailingSpace;
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
        // Filters are deprecated in Vue 3, use the mixin methods instead
        // Vue.filter("localize", l);
        // Vue.filter("l", l);
        Vue.directive("localize", localizeDirective(l));
        Vue.mixin(localizeMixin(l));
        // Make l globally available as a property
        Vue.config.globalProperties.l = l;
        Vue.config.globalProperties.localize = l;
    },
};
