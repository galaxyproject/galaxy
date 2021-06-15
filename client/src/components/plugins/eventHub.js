/**
 * Mixin provides global event bus other than $root.$emit. Avoids event naming conflicts and makes
 * opt-in possible, also works when components aren't part of the same Vue app tree as is often the
 * case with our app until backbone is gone.
 */

import Vue from "vue";

export const eventHub = new Vue();

export const eventHubMixin = {
    created() {
        this.eventHub = eventHub;
    },
};

export const eventHubPlugin = {
    install(Vue) {
        Vue.mixin(eventHubMixin);
    },
};
