/**
 * Central Vuex store
 */

import config from "config";
import localForage from "localforage";
import Vue from "vue";
import Vuex from "vuex";
import createCache from "vuex-cache";
import VuexPersistence from "vuex-persist";

import { datasetExtFilesStore } from "./datasetExtFilesStore";
import { datasetPathDestinationStore } from "./datasetPathDestinationStore";
import { gridSearchStore } from "./gridSearchStore";
import { invocationStore } from "./invocationStore";
import { jobDestinationParametersStore } from "./jobDestinationParametersStore";
import { syncVuextoGalaxy } from "./syncVuextoGalaxy";
import { tagStore } from "./tagStore";

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
            destinationParameters: jobDestinationParametersStore,
            datasetExtFiles: datasetExtFilesStore,
            datasetPathDestination: datasetPathDestinationStore,
            invocations: invocationStore,
            gridSearch: gridSearchStore,
            tags: tagStore,
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
