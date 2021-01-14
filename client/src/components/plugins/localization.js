/**
 * Makes localization directives and filters available
 */

import _l from "utils/localization";

const newlineMatch = /\r?\n|\r/g;
const doublespaces = /\s\s+/g;

const localizeDirective = {
    bind(el, binding, vnode) {
        el.childNodes.forEach((node) => {
            const oneline = node.textContent.replace(newlineMatch, " ");
            const singleSpaces = oneline.replace(doublespaces, " ");
            node.textContent = _l(singleSpaces);
        });
    },
};

export const localizationPlugin = {
    install(Vue) {
        Vue.filter("localize", _l);
        Vue.filter("l", _l);
        Vue.directive("localize", localizeDirective);
    },
};
