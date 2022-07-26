import { getCurrentUser } from "./queries";
import User from "./User";

const state = {
    currentUser: null,
};

const getters = {
    // Store user as plain json props so we can
    // persist it easily in localStorage or something,
    // hydrate with model object using the getter
    currentUser(state) {
        const userProps = state.currentUser || {};
        const user = new User(userProps);
        return Object.freeze(user);
    },
};

const mutations = {
    setCurrentUser(state, user) {
        state.currentUser = user;
    },
};

// Holds promise for in-flight loads
let loadPromise;

const actions = {
    loadUser({ dispatch }) {
        if (!loadPromise) {
            loadPromise = getCurrentUser()
                .then((user) => {
                    dispatch("setCurrentUser", user);
                })
                .catch((err) => {
                    console.warn("loadUser error", err);
                })
                .finally(() => {
                    loadPromise = null;
                });
        }
    },
    async setCurrentUser({ commit, dispatch }, user) {
        commit("setCurrentUser", user);
        dispatch("history/loadCurrentHistory", user, { root: true });
        dispatch("history/loadHistories", user, { root: true });
    },
};

export const userStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
