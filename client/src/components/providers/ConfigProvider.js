/**
 * ConfigProvider ensures that the configs have been loaded from the server and
 * delivers all the config values onto the slotProps. Basically it just exists
 * to house the load method in a lifecycle handler because Vuex can't do that
 * for itself.
 */

import { mapGetters, mapActions } from "vuex";
import Vue from "vue"; // this module's Vue is different from store/index.js' Vue
import Vuex from "vuex";

Vue.use(Vuex);

export default {
    computed: {
        ...mapGetters("config", ["config"]),
    },
    methods: {
        ...mapActions("config", ["loadConfigs"]),
    },
    created() {
        this.loadConfigs();
    },
    render() {
        return this.$scopedSlots.default({ config: this.config, loading: this.config === undefined });
    },
};
