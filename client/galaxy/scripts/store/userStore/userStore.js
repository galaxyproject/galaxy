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
        let userProps = state.currentUser;
        if (!userProps) {
            // TODO: remove when we no longer use the galaxy instance
            try {
                userProps = window.Galaxy.user;
            } catch (err) {
                console.warn(err);
            }
        }
        return new User(userProps);
    },
};

const mutations = {
    setCurrentUser(state, user) {
        state.currentUser = user;
    },
};

const actions = {
    async loadUser({ commit, dispatch }) {
        const user = await getCurrentUser();
        commit("setCurrentUser", user);
    },
    async $init({ dispatch }) {
        await dispatch("loadUser");
    },
};

export const userStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
