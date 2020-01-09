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
        <font-awesome-icon :icon="['far', 'star']" />
    </a>
</template>

<script>
import { VBTooltip } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar } from "@fortawesome/free-regular-svg-icons";
library.add(faStar);

export default {
    name: "FavoritesButton",
    components: { FontAwesomeIcon },
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
