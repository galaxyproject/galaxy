import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

import { of } from "rxjs";
import { map } from "rxjs/operators";
import { monitorContentQuery, cacheContent } from "../components/History/caching";

const state = {
    datasetByHDAId: {},
};

const getters = {
    getDatasetById: (state) => (hda_id) => {
        return state.datasetByHDAId[hda_id];
    },
};

const actions = {
    fetchDataset: async ({ commit }, hda_id) => {
        // if we're certain that the store is always up to date
        // we could skip the fetch.
        const { data } = await axios.get(`${getAppRoot()}api/datasets/${hda_id}`);
        await cacheContent(data);
        commit("saveDatasetForHDAId", { hda_id, dataset: data });
        return state.datasetByHDAId[hda_id];
    },
    async $init({ dispatch }, { store }) {
        // check pouchdb for updates to all datasets
        // if that becomes too expensive we could just monitor state.datasetByHDAId
        const selector = { selector: { history_content_type: { $eq: "dataset" } } };
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
            next: (doc) => doc && store.commit("datasets/saveDatasetForHDAId", { hda_id: doc.id, dataset: doc }),
            error: (err) => console.error(err),
            complete: () => console.log("Completed dataset subscription"),
        });
    },
};

const mutations = {
    saveDatasetForHDAId: (state, { hda_id, dataset }) => {
        Vue.set(state.datasetByHDAId, hda_id, dataset);
    },
};

export const datasetsStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
