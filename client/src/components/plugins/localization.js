/**
 * Makes localization directives and filters available
 */

import _l from "utils/localization";

const newlineMatch = /\r?\n|\r/g;
const doublespaces = /\s\s+/g;

const localizeDirective = {
    // TODO consider using a different hook if we need dynamic updates in content translation
    bind(el, binding, vnode) {
        el.childNodes.forEach((node) => {
            const standardizedContent = node.textContent.replace(newlineMatch, " ").replace(doublespaces, " ").trim();
            node.textContent = _l(standardizedContent);
        });
    },
};

// adds localizeText mixin
const localizeMixin = {
    methods: {
        l: _l,
        localize: _l,
    },
};

export const localizationPlugin = {
    install(Vue) {
        Vue.filter("localize", _l);
        Vue.filter("l", _l);
        Vue.directive("localize", localizeDirective);
        Vue.mixin(localizeMixin);
    },
};
