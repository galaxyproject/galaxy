export const state = {
    biocomputeDetailsById: {},
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    getBioComputeById: (state) => (invocationId) => {
        return state.biocomputeDetailsById[invocationId];
    },
};

const actions = {
    fetchIBiocomputeForId: async ({ commit }, invocationId) => {
        const { data } = await axios.get(`${getAppRoot()}api/invocations/${invocationId}/export_bco`);
        console.log(typeof(invocationId));
        commit("saveBiocomputeForId", { invocationId, biocomputeData: data });
    },
    cloneBioComputeInfo: async ({ commit, dispatch, getters }, invocationId) => {
        
        // Save the "User" version of the BCO, meaning the version that can be edited
        // by the user by changing inputs on the page.

        // Wait for the fetch.
        await dispatch('fetchIBiocomputeForId', invocationId);

        // Get the info.
        let bco_info = getters.getBioComputeById(invocationId);

        // Write the clone.
        let user_version_id = invocationId + 'USER';
        console.log(typeof(invocationId));
        console.log('test start');
        console.log(user_version_id);
        console.log(bco_info);
        console.log('test end');
        commit("saveBiocomputeForId", { user_version_id, biocomputeData: bco_info });

    }
};

const mutations = {
    saveBiocomputeForId: (state, { invocationId, biocomputeData }) => {
        console.log(invocationId);
        console.log(biocomputeData);
        Vue.set(state.biocomputeDetailsById, invocationId, biocomputeData);
    },
    updateBCOInfo: ({ invocationId, jsonpath }) => {

        // Update the object based on new input.

        // Arguments

        // invocationId:  The invocation ID.
        // jsonpath:  The flattened JSON path to write to.
        

        // Compose the user version of the invocation ID.
        var working_id = invocationId + '-USER'

        // Call the getter to get the user data.

        // Source:  https://stackoverflow.com/questions/52048944/vuex-call-getters-from-action
        var user_BCO = getters.getBioComputeById(working_id);

    },
};

export const biocomputeStore = {
    state,
    getters,
    actions,
    mutations,
};
