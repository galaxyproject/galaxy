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
        if (state.currentUser !== null) {
            const userProps = state.currentUser;
            const user = new User(userProps);
            return Object.freeze(user);
        }
        return state.currentUser;
    },
};

const mutations = {
    setCurrentUser(state, user) {
        state.currentUser = Object.freeze(user);
    },
};

// Holds promise for in-flight loads
let loadPromise;

const actions = {
    loadUser({ state, dispatch }, force = false) {
        if ((!state.currentUser || force) && !loadPromise) {
            loadPromise = getCurrentUser()
                .then((user) => {
                    console.log("user", user);
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
    async setCurrentUser({ commit, dispatch, getters }, user) {
        if (!(getters.currentUser && getters.currentUser.isSameUser(new User(user)))) {
            commit("setCurrentUser", user);
            await dispatch("betaHistory/loadUserHistories", user, { root: true });
        }
    },
};

export const userStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
