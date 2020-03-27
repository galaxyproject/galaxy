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
import { historyStore } from "./historyStore";
import { userStore } from "./userStore";
import { configStore } from "./configStore";
import { workflowStore } from "./workflowStore";

Vue.use(Vuex);

export function createStore() {
    return new Vuex.Store({
        plugins: [
            createCache(),
            (store) => {
                store.dispatch("user/$init", { store });
                store.dispatch("config/$init", { store });
            },
        ],
        modules: {
            gridSearch: gridSearchStore,
            histories: historyStore,
            tags: tagStore,
            jobMetrics: jobMetricsStore,
            invocations: invocationStore,
            user: userStore,
            config: configStore,
            workflows: workflowStore,
        },
    });
}

const store = createStore();

export default store;
