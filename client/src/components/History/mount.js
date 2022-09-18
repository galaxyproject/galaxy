/**
 * Endpoint for mounting History in non-Vue environment.
 */
import Vue from "vue";
import HistoryView from "./HistoryView";
import store from "store";

export const mountHistory = (el, propsData) => {
    const component = Vue.extend(HistoryView);
    return new component({
        store: store,
        propsData: propsData,
        el: el,
    });
};
