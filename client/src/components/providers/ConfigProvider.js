/**
 * DEPRECATED: instead use 'useConfigStore'
 * ConfigProvider ensures that the configs have been loaded from the server and
 * delivers all the config values onto the slotProps.
 */

import { mapActions, mapState } from "pinia";

import { useConfigStore } from "@/stores/configurationStore";

export default {
    computed: {
        ...mapState(useConfigStore, ["config"]),
    },
    methods: {
        ...mapActions(useConfigStore, ["loadConfig"]),
    },
    created() {
        this.loadConfig();
    },
    render() {
        return this.$scopedSlots.default({ config: this.config, loading: this.config === undefined });
    },
};
