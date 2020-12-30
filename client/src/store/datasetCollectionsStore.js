import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { of } from "rxjs";
import { map } from "rxjs/operators";
import { monitorContentQuery, cacheContent } from "../components/History/caching";

const state = {
    datasetCollectionByHDCAId: {},
};

const getters = {
    getDatasetCollectionById: (state) => (hdca_id) => {
        return state.datasetCollectionByHDCAId[hdca_id];
    },
};

const actions = {
    fetchDatasetCollection: async ({ commit }, hdca_id) => {
        // if we're certain that the store is always up to date
        // we could skip the fetch.

        const { data } = await axios.get(`${getAppRoot()}api/dataset_collections/${hdca_id}?instance_type=history`);
        const cachedData = await cacheContent(data, true);
        commit("saveCollectionForHDCAId", { hdca_id, dataset_collection: cachedData });
        return state.datasetCollectionByHDCAId[hdca_id];
    },
    async $init({ dispatch }, { store }) {
        // check pouchdb for updates to all datasets
        // if that becomes too expensive we could just monitor state.datasetCollectionByHDCAId
        const selector = { selector: { history_content_type: { $eq: "dataset_collection" } } };
        const monitorUpdate$ = of(selector).pipe(
            monitorContentQuery(),
            map((update) => {
                const { initialMatches = [], doc = null, deleted } = update;
                if (deleted) {
                    return null;
                }
                let updatedDoc = doc;
                if (initialMatches.length == 1) {
                    updatedDoc = initialMatches[0];
                }
                return updatedDoc;
            })
        );
        monitorUpdate$.subscribe({
            next: (doc) =>
                doc &&
                store.commit("datasetCollections/saveCollectionForHDCAId", {
                    hdca_id: doc.id,
                    dataset_collection: doc,
                }),
            error: (err) => console.error(err),
            complete: () => console.log("Completed dataset_collection subscription"),
        });
    },
};

const mutations = {
    saveCollectionForHDCAId: (state, { hdca_id, dataset_collection }) => {
        console.log("Saving HDCA");
        Vue.set(state.datasetCollectionByHDCAId, hdca_id, dataset_collection);
    },
};

export const datasetCollectionsStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
