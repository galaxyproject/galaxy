<template>
    <b-button
        class="panel-header-button-toolbox"
        @click="onFavorites"
        v-b-tooltip.hover
        :title="tooltipText"
        href="javascript:void(0)"
        role="button"
        size="sm"
        variant="link"
        aria-label="Show favorite tools">
        <font-awesome-icon v-if="toggle" :icon="['fas', 'star']" />
        <font-awesome-icon v-else :icon="['far', 'star']" />
    </b-button>
</template>

<script>
import _l from "utils/localization";
import { VBTooltip } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar } from "@fortawesome/free-regular-svg-icons";
import { faStar as faStarSolid } from "@fortawesome/free-solid-svg-icons";

library.add(faStar);
library.add(faStarSolid);

export default {
    name: "FavoritesButton",
    props: {
        query: {
            type: String,
        },
    },
    components: { FontAwesomeIcon },
    data() {
        return {
            searchKey: "#favorites",
            tooltipToggle: _l("Show favorites"),
            tooltipUntoggle: "Clear",
            toggle: false,
        };
    },
    directives: {
        "v-b-tooltip": VBTooltip,
    },
    watch: {
        query() {
            this.toggle = this.query == this.searchKey;
        },
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
