<template>
    <b-button
        v-b-tooltip.hover
        class="panel-header-button-toolbox"
        size="sm"
        variant="link"
        aria-label="Toolbox Filter Settings"
        :title="tooltip"
        @click="onFilter">
        <icon v-if="activeFilters === 0" :icon="['glr', 'filter']" />
        <icon v-else :icon="['gls', 'filter']" />
    </b-button>
</template>

<script>
import _l from "utils/localization";

export default {
    name: "FiltersButton",
    computed: {
        activeFilters() {
            const user = this.$store.state.user.currentUser;

            if (!user || !user.id) {
                return 0;
            }

            const preferences = user.preferences;
            const labelFilters = preferences.toolbox_label_filters?.split(",") ?? [];
            const sectionFilters = preferences.toolbox_section_filters?.split(",") ?? [];
            const toolFilters = preferences.toolbox_tool_filters?.split(",") ?? [];

            return [...labelFilters, ...sectionFilters, ...toolFilters].filter((s) => s !== "").length;
        },
        tooltip() {
            if (this.activeFilters === 0) {
                return _l("Toolbox Filter Settings");
            } else if (this.activeFilters === 1) {
                return _l("1 Filter Active");
            } else {
                return this.activeFilters + " " + _l("Filters Active");
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
