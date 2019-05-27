/**
 * Central Vuex store
 */

import Vue from "vue";
import Vuex from "vuex";
import createCache from "vuex-cache";

import { gridSearchStore } from "./gridSearchStore";
import { tagStore } from "./tagStore";
import { jobMetricsStore } from "./jobMetricsStore";

Vue.use(Vuex);

export default new Vuex.Store({
    plugins: [createCache()],
    modules: {
        gridSearch: gridSearchStore,
        tags: tagStore,
        jobMetrics: jobMetricsStore
    }
});
