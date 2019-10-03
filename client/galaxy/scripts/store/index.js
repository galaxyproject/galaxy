/**
 * Central Vuex store
 */

import Vue from "vue";
import Vuex from "vuex";
import createCache from "vuex-cache";

import { gridSearchStore } from "./gridSearchStore";
import { tagStore } from "./tagStore";
import { jobMetricsStore } from "./jobMetricsStore";
import { invocationStore } from "./invocationStore";

Vue.use(Vuex);

export function createStore() {
    return new Vuex.Store({
        plugins: [createCache()],
        modules: {
            gridSearch: gridSearchStore,
            tags: tagStore,
            jobMetrics: jobMetricsStore,
            invocations: invocationStore
        }
    });
}

const store = createStore();

export default store;
