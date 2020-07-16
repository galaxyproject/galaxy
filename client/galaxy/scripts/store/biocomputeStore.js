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
        commit("saveBiocomputeForId", { invocationId, biocomputeData: data });

        // Save the "User" version of the BCO, meaning the version that can be edited
        // by the user by changing inputs on the page.
        //var user_version_id = invocationId + '-USER';
        //commit("saveBiocomputeForId", { user_version_id, biocomputeData: data });

    },
    updateBCOInfo: ({ getters, invocationId, jsonpath }) => {

        // Update the object based on new input.

        // Arguments

        // invocationId:  The invocation ID.
        // jsonpath:  The flattened JSON path to write to.
        

        // Compose the user version of the invocation ID.
        var working_id = invocationId + '-USER'

        // Call the getter to get the user data.

        // Source:  https://stackoverflow.com/questions/52048944/vuex-call-getters-from-action
        var user_BCO = getters.getBioComputeById(working_id);

        console.log(user_BCO);

    },
};

const mutations = {
    saveBiocomputeForId: (state, { invocationId, biocomputeData }) => {
        console.log(invocationId);
        console.log(biocomputeData);
        Vue.set(state.biocomputeDetailsById, invocationId, biocomputeData);
        console.log('FINISHED');
    },
};

export const biocomputeStore = {
    state,
    getters,
    actions,
    mutations,
};
