/**
 * Endpoint for mounting History in non-Vue environment.
 */
import Vue from "vue";
import VueRouter from "vue-router";
import HistoryView from "./HistoryView";
import store from "store";
import { safePath } from "utils/redirect";

Vue.use(VueRouter);

export const mountHistory = (el, propsData) => {
    const component = Vue.extend(HistoryView);
    const router = new VueRouter();
    router.push = (url) => {
        window.location.href = safePath(url);
    };
    return new component({
        el: el,
        propsData: propsData,
        router: router,
        store: store,
    });
};
