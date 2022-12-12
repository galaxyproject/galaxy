/**
 * Central Vuex store
 */

import localForage from "localforage";
import Vue from "vue";
import Vuex from "vuex";
import createCache from "vuex-cache";
import VuexPersistence from "vuex-persist";

import config from "config";

import { jobStore } from "./../stores/jobStore";
import { collectionAttributesStore } from "./collectionAttributesStore";
import { configStore } from "./configStore";
import { datasetExtFilesStore } from "./datasetExtFilesStore";
import { datasetPathDestinationStore } from "./datasetPathDestinationStore";
import { gridSearchStore } from "./gridSearchStore";
import { collectionElementsStore, datasetStore, historyItemsStore, historyStore } from "./historyStore";
import { invocationStore } from "./invocationStore";
import { jobDestinationParametersStore } from "./jobDestinationParametersStore";
import { jobMetricsStore } from "./jobMetricsStore";
import { panelStore } from "./panelStore";
import { tagStore } from "./tagStore";
import { toolStore } from "./toolStore";
import { userFlagsStore, userStore } from "./userStore";

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
    reducer: (state) => {
        const { panels, userFlags } = state;
        return {
            panels,
            userFlags,
        };
    },
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
            informationStore: jobStore,
            invocations: invocationStore,
            jobMetrics: jobMetricsStore,
            gridSearch: gridSearchStore,
            history: historyStore,
            historyItems: historyItemsStore,
            panels: panelStore,
            tags: tagStore,
            tools: toolStore,
            user: userStore,
            userFlags: userFlagsStore,
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
