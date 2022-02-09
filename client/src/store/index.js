/**
 * Central Vuex store
 */

import Vue from "vue";
import Vuex from "vuex";
import createCache from "vuex-cache";
import VuexPersistence from "vuex-persist";

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
import { collectionAttributesStore } from "./collectionAttributesStore";
import { genomeStore } from "./genomeStore";
import { datatypeStore } from "./datatypeStore";
import { panelStore } from "./panelStore";

// beta features
import { historyStore as betaHistoryStore } from "components/History/model/historyStore";

// Syncs vuex to Galaxy store until Galaxy vals to not exist
import { syncVuextoGalaxy } from "./syncVuextoGalaxy";

Vue.use(Vuex);

// Create vuexpersistence
const panelsPersistence = new VuexPersistence({
    storage: window.localStorage,
    modules: ["panels"],
});

export function createStore() {
    const storeConfig = {
        plugins: [createCache(), panelsPersistence.plugin],
        modules: {
            user: userStore,
            config: configStore,
            betaHistory: betaHistoryStore,
            panels: panelStore,

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
            collectionAttributesStore: collectionAttributesStore,
            genomeStore: genomeStore,
            datatypeStore: datatypeStore,
        },
    };

    // Watches for changes in Galaxy and sets those values on Vuex until Galaxy is gone
    // TODO: remove subscriptions in syncVuexToGalaxy as legacy functionality is ported to Vue
    if (!config.testBuild) {
        storeConfig.plugins.push(syncVuextoGalaxy);
    }

    return new Vuex.Store(storeConfig);
}

const store = createStore();

export default store;
