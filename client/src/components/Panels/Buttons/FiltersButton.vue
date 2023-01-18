<template>
    <b-button
        v-b-tooltip.hover
        class="panel-header-button-toolbox"
        size="sm"
        variant="link"
        aria-label="Toolbox Filter Settings"
        :disabled="currentUser.isAnonymous"
        :title="tooltip"
        @click="onFilter">
        <icon v-if="activeFilters === 0" :icon="['glr', 'filter']" />
        <icon v-else :icon="['gls', 'filter']" />
    </b-button>
</template>

<script>
import { mapGetters } from "vuex";

export default {
    name: "FiltersButton",
    computed: {
        ...mapGetters("user", ["currentUser"]),
        activeFilters() {
            const user = this.currentUser;

            if (!user || !user.id || user.isAnonymous) {
                return 0;
            }

            const preferences = user.preferences;
            const labelFilters = preferences.toolbox_label_filters?.split(",") ?? [];
            const sectionFilters = preferences.toolbox_section_filters?.split(",") ?? [];
            const toolFilters = preferences.toolbox_tool_filters?.split(",") ?? [];

            return [...labelFilters, ...sectionFilters, ...toolFilters].filter((s) => s !== "").length;
        },
        tooltip() {
            if (this.currentUser.isAnonymous) {
                return this.l("Log in to Filter Toolbox");
            }

            if (this.activeFilters === 0) {
                return this.l("Toolbox Filter Settings");
            } else if (this.activeFilters === 1) {
                return this.l("1 Filter Active");
            } else {
                return this.activeFilters + " " + this.l("Filters Active");
            }
        },
    },
    methods: {
        onFilter() {
            this.$router.push("/user/toolbox_filters");
        },
    },
};
</script>
