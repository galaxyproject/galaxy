/**
 * Central Vuex store
 */

import config from "config";
import localForage from "localforage";
import Vue from "vue";
import Vuex from "vuex";
import createCache from "vuex-cache";
import VuexPersistence from "vuex-persist";

import { collectionAttributesStore } from "./collectionAttributesStore";
import { datasetExtFilesStore } from "./datasetExtFilesStore";
import { datasetPathDestinationStore } from "./datasetPathDestinationStore";
import { gridSearchStore } from "./gridSearchStore";
import { collectionElementsStore, datasetStore } from "./historyStore";
import { invocationStore } from "./invocationStore";
import { jobDestinationParametersStore } from "./jobDestinationParametersStore";
import { panelStore } from "./panelStore";
import { syncVuextoGalaxy } from "./syncVuextoGalaxy";
import { tagStore } from "./tagStore";
import { toolStore } from "./toolStore";

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
        const { panels } = state;
        return {
            panels,
        };
    },
});

export function createStore() {
    const storeConfig = {
        plugins: [createCache(), panelsPersistence.plugin],
        modules: {
            collectionAttributesStore: collectionAttributesStore,
            collectionElements: collectionElementsStore,
            destinationParameters: jobDestinationParametersStore,
            dataset: datasetStore,
            datasetExtFiles: datasetExtFilesStore,
            datasetPathDestination: datasetPathDestinationStore,
            invocations: invocationStore,
            gridSearch: gridSearchStore,
            panels: panelStore,
            tags: tagStore,
            tools: toolStore,
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
