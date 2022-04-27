<template>
    <b-button
        v-b-tooltip.hover
        class="panel-header-button-toolbox"
        size="sm"
        variant="link"
        aria-label="Show favorite tools"
        :title="tooltipText"
        @click="onFavorites">
        <icon v-if="toggle" :icon="['fas', 'star']" />
        <icon v-else :icon="['far', 'star']" />
    </b-button>
</template>

<script>
import _l from "utils/localization";

export default {
    name: "FavoritesButton",
    props: {
        query: {
            type: String,
        },
    },
    data() {
        return {
            searchKey: "#favorites",
            tooltipToggle: _l("Show favorites"),
            tooltipUntoggle: "Clear",
            toggle: false,
        };
    },
    computed: {
        tooltipText() {
            if (this.toggle) {
                return this.tooltipUntoggle;
            } else {
                return this.tooltipToggle;
            }
        },
    },
    watch: {
        query() {
            this.toggle = this.query == this.searchKey;
        },
    },
    methods: {
        onFavorites() {
            this.toggle = !this.toggle;
            if (this.toggle) {
                this.$emit("onFavorites", this.searchKey);
            } else {
                this.$emit("onFavorites", null);
            }
        },
    },
};
</script>
