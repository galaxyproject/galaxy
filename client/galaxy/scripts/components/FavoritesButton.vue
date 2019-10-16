<template>
    <a
        class="panel-header-button"
        @click="showFavorites"
        v-b-tooltip.hover
        :title="tooltipText"
        href="javascript:void(0)"
        role="button"
        aria-label="Show favorite tools"
    >
        <span class="fa fa-star-o"></span>
    </a>
</template>

<script>
import { VBTooltip } from "bootstrap-vue";

export default {
    name: "FavoritesButton",
    data() {
        return {
            tooltipText: "Show favorites"
        };
    },
    directives: {
        "v-b-tooltip": VBTooltip
    },
    methods: {
        showFavorites() {
            // FIXME: use Vue communication for this
            const toolSearchQueryNode = document.querySelector(".tool-search-query");

            if (toolSearchQueryNode.value.startsWith("#fav")) {
                toolSearchQueryNode.value = "";
                toolSearchQueryNode.dispatchEvent(new Event("input"));
                this.tooltipText = "Hide favorites";
            } else {
                toolSearchQueryNode.value = "#favorites";
                toolSearchQueryNode.dispatchEvent(new Event("input"));
                this.tooltipText = "Show favorites";
            }
        }
    }
};
</script>

<style scoped></style>
