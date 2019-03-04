/**
 * Central Vuex store
 */

import Vue from "vue";
import Vuex from "vuex";
import { gridSearchStore as gridSearch } from "./gridSearchStore";

Vue.use(Vuex);

export default new Vuex.Store({
    modules: { gridSearch }
});
