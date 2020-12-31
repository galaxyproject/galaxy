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
import { toolStore } from "./toolStore";
import { datasetPathDestinationStore } from "./datasetPathDestinationStore";
import { datasetExtFilesStore } from "./datasetExtFilesStore";
import { jobStore } from "./jobStore";

// beta features
import { historyStore as betaHistoryStore } from "components/History/model/historyStore";

// Syncs vuex to Galaxy store until Galaxy vals to not exist
import { syncVuextoGalaxy } from "./syncVuextoGalaxy";

Vue.use(Vuex);

export function createStore() {
    const storeConfig = {
        plugins: [createCache()],
        modules: {
            user: userStore,
            config: configStore,
            betaHistory: betaHistoryStore,

            // TODO: please namespace all store modules
            gridSearch: gridSearchStore,
            histories: historyStore,
            tags: tagStore,
            jobMetrics: jobMetricsStore,
            destinationParameters: jobDestinationParametersStore,
            datasetPathDestination: datasetPathDestinationStore,
            datasetExtFiles: datasetExtFilesStore,
            invocations: invocationStore,
            workflows: workflowStore,
            informationStore: jobStore,
            tools: toolStore,
            datasets: datasetsStore,
            datasetCollections: datasetCollectionsStore,
        },
    };

    // Initializes global store elements.
    // Vuex can't lazy-load, so we much manually insert global data at some point and we currently
    // don't have a root App component container (which is traditionally used for such operations).
    if (!config.testBuild) {
        // TODO: remove all automagic inits in favor of provider mechanism which will trigger a load
        // using a lifecycle hook, or alternatively switch from Vuex to an observable framework
        // capable of lazy-loading on request
        storeConfig.plugins.push((store) => {
            store.dispatch("user/loadUser", { store });
            store.dispatch("config/loadConfigs", { store });
            store.dispatch("betaHistory/$init", { store });
        });

        // Watches for changes in Galaxy and sets those values on Vuex until Galaxy is gone
        // TODO: remove subscriptions in syncVuexToGalaxy as legacy functionality is ported to Vue
        storeConfig.plugins.push(syncVuextoGalaxy);
    }

    return new Vuex.Store(storeConfig);
}

const store = createStore();

export default store;
