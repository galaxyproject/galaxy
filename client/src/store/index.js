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
import { userStore, syncUserToGalaxy } from "./userStore";
import { configStore } from "./configStore";
import { workflowStore } from "./workflowStore";
import { datasetPathDestinationStore } from "./datasetPathDestinationStore";
import { datasetExtFilesStore } from "./datasetExtFilesStore";
import { datasetsStore } from "./datasetsStore";
import { jobStore } from "./jobStore";

// beta features
import { historyStore as betaHistoryStore } from "components/History/model/historyStore";
import { syncCurrentHistoryToGalaxy } from "components/History/model/syncCurrentHistoryToGalaxy";

Vue.use(Vuex);

export function createStore() {
    const storeConfig = {
        plugins: [createCache()],
        modules: {
            // TODO: namespace all these modules
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
            betaHistory: betaHistoryStore,
        },
    };

    // Initialize state

    if (!config.testBuild) {
        storeConfig.plugins.push((store) => {
            store.dispatch("config/$init", { store });
            store.dispatch("user/$init", { store });
            store.dispatch("betaHistory/$init", { store });
        });
    }

    // Create watchers to monitor legacy galaxy instance for important values

    syncUserToGalaxy((user) => {
        store.commit("user/setCurrentUser", user);
    });

    syncCurrentHistoryToGalaxy((id) => {
        store.commit("betaHistory/setCurrentHistoryId", id);
    });

    return new Vuex.Store(storeConfig);
}

const store = createStore();

export default store;
