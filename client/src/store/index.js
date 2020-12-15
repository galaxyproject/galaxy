/**
 * Central Vuex store
 */

import Vue from "vue";
import Vuex from "vuex";
import createCache from "vuex-cache";
import config from "config";

import { gridSearchStore } from "./gridSearchStore";
import { tagStore } from "./tagStore";
import { jobMetricsStore } from "./jobMetricsStore";
import { jobDestinationParametersStore } from "./jobDestinationParametersStore";
import { invocationStore } from "./invocationStore";
import { historyStore } from "./historyStore";
import { userStore } from "./userStore";
import { configStore } from "./configStore";
import { workflowStore } from "./workflowStore";
import { datasetPathDestinationStore } from "./datasetPathDestinationStore";
import { datasetExtFilesStore } from "./datasetExtFilesStore";
import { datasetsStore } from "./datasetsStore";
import { jobStore } from "./jobStore";

// beta features
import { historyStore as betaHistoryStore } from "components/History/model/historyStore";

Vue.use(Vuex);

export function createStore() {
    const storeConfig = {
        plugins: [createCache()],
        modules: {
            gridSearch: gridSearchStore,
            histories: historyStore,
            tags: tagStore,
            jobMetrics: jobMetricsStore,
            destinationParameters: jobDestinationParametersStore,
            datasetPathDestination: datasetPathDestinationStore,
            datasetExtFiles: datasetExtFilesStore,
            invocations: invocationStore,
            user: userStore,
            config: configStore,
            workflows: workflowStore,
            datasets: datasetsStore,
            informationStore: jobStore,
        },
    };

    // Initialize store
    if (!config.testBuild) {
        storeConfig.plugins.push((store) => {
            store.dispatch("user/$init", { store });
            store.dispatch("config/$init", { store });
        });
    }

    const useBetaHistory = sessionStorage.getItem("useBetaHistory");
    if (useBetaHistory) {
        storeConfig.modules.betaHistory = betaHistoryStore;
        storeConfig.plugins.push((store) => {
            store.dispatch("betaHistory/$init", { store });
        });
    }

    return new Vuex.Store(storeConfig);
}

const store = createStore();

export default store;
