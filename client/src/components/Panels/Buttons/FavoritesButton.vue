<template>
    <b-button
        v-b-tooltip.hover
        class="panel-header-button-toolbox"
        size="sm"
        variant="link"
        aria-label="Show favorite tools"
        :disabled="isAnonymous"
        :title="tooltipText"
        @click="onFavorites">
        <icon v-if="toggle" :icon="['fas', 'star']" />
        <icon v-else :icon="['far', 'star']" />
    </b-button>
</template>

<script>
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";

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
            toggle: false,
        };
    },
    computed: {
        ...mapState(useUserStore, ["isAnonymous"]),
        tooltipText() {
            if (this.isAnonymous) {
                return this.l("Log in to Favorite Tools");
            } else {
                if (this.toggle) {
                    return this.l("Clear");
                } else {
                    return this.l("Show favorites");
                }
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
