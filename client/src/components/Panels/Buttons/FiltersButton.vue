<template>
    <b-button
        v-b-tooltip.hover
        class="panel-header-button-toolbox"
        size="sm"
        variant="link"
        aria-label="Toolbox Filter Settings"
        :title="tooltip"
        @click="onFilter">
        <icon icon="filter" />
    </b-button>
</template>

<script>
import _l from "utils/localization";

export default {
    name: "FiltersButton",
    data() {
        return {
            tooltip: _l("Toolbox Filter Settings"),
        };
    },
    methods: {
        onFilter() {
            this.$router.push("/user/toolbox_filters");
        },
    },
};
</script>
