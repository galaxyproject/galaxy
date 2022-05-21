/**
 * Central Vuex store
 */

import Vue from "vue";
import Vuex from "vuex";
import createCache from "vuex-cache";
import VuexPersistence from "vuex-persist";
import localForage from "localforage";

import config from "config";

import { gridSearchStore } from "./gridSearchStore";
import { tagStore } from "./tagStore";
import { jobMetricsStore } from "./jobMetricsStore";
import { jobDestinationParametersStore } from "./jobDestinationParametersStore";
import { invocationStore } from "./invocationStore";
import { collectionElementsStore, datasetStore, historyItemsStore, historyStore } from "./historyStore";
import { userStore, userFlagsStore } from "./userStore";
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

// Syncs vuex to Galaxy store until Galaxy vals to not exist
import { syncVuextoGalaxy } from "./syncVuextoGalaxy";

Vue.use(Vuex);

const galaxyStorage = localForage.createInstance({});
galaxyStorage.config({
    driver: [localForage.INDEXEDDB, localForage.LOCALSTORAGE],
    name: "galaxyIndexedDB",
    version: 1.0,
    storeName: "galaxyStore",
});

const panelsPersistence = new VuexPersistence({
    storage: galaxyStorage,
    asyncStorage: true,
    modules: ["panels", "userFlags"],
});

export function createStore() {
    const storeConfig = {
        plugins: [createCache(), panelsPersistence.plugin],
        modules: {
            collectionAttributesStore: collectionAttributesStore,
            collectionElements: collectionElementsStore,
            config: configStore,
            destinationParameters: jobDestinationParametersStore,
            dataset: datasetStore,
            datasetExtFiles: datasetExtFilesStore,
            datasetPathDestination: datasetPathDestinationStore,
            datatypeStore: datatypeStore,
            informationStore: jobStore,
            invocations: invocationStore,
            jobMetrics: jobMetricsStore,
            genomeStore: genomeStore,
            gridSearch: gridSearchStore,
            history: historyStore,
            historyItems: historyItemsStore,
            panels: panelStore,
            tags: tagStore,
            tools: toolStore,
            user: userStore,
            userFlags: userFlagsStore,
            workflows: workflowStore,
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
