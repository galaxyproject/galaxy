import { addFavoriteTool, removeFavoriteTool, getCurrentUser, setCurrentTheme } from "./queries";
import User from "./User";

const state = {
    currentUser: null,
    currentPreferences: null,
};

const getters = {
    // Store user as plain json props so we can
    // persist it easily in localStorage or something,
    // hydrate with model object using the getter
    currentUser(state) {
        const userProps = state.currentUser ?? {};
        const user = new User(userProps);
        return Object.freeze(user);
    },
    currentTheme(state) {
        return state.currentPreferences?.theme ?? null;
    },
    currentFavorites(state) {
        const preferences = state.currentPreferences;
        if (preferences && preferences.favorites) {
            return JSON.parse(preferences.favorites);
        } else {
            return { tools: [] };
        }
    },
};

const mutations = {
    setCurrentUser(state, user) {
        state.currentUser = user;
        state.currentPreferences = user?.preferences ?? null;
    },
    setCurrentTheme(state, theme) {
        if (state.currentPreferences) {
            state.currentPreferences.theme = theme;
        }
    },
    setFavoriteTools(state, tools) {
        if (state.currentPreferences) {
            const favorites = state.currentPreferences.favorites;
            const favoritesDict = favorites ? JSON.parse(favorites) : { tools: [] };
            favoritesDict.tools = tools;
            state.currentPreferences.favorites = JSON.stringify(favoritesDict);
        }
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
    async setCurrentTheme({ commit, state }, theme) {
        const currentTheme = await setCurrentTheme(state.currentUser.id, theme);
        commit("setCurrentTheme", currentTheme);
    },
    async addFavoriteTool({ commit, state }, toolId) {
        const tools = await addFavoriteTool(state.currentUser.id, toolId);
        commit("setFavoriteTools", tools);
    },
    async removeFavoriteTool({ commit, state }, toolId) {
        const tools = await removeFavoriteTool(state.currentUser.id, toolId);
        commit("setFavoriteTools", tools);
    },
};

export const userStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
