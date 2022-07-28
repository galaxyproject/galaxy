<template>
    <b-link v-b-tooltip.hover :title="title" class="workflow-bookmark-link" @click="onClick">
        <font-awesome-icon v-if="checked" :icon="['fas', 'star']" />
        <font-awesome-icon v-else :icon="['far', 'star']" />
    </b-link>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink } from "bootstrap-vue";
import { VBTooltip } from "bootstrap-vue";

import { faStar } from "@fortawesome/free-solid-svg-icons";
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
library.add(faStar, farStar);

const CHECKED_DESCRIPTION =
    "This workflow is currently bookmarked, click this link to remove this bookmark for this workflow.";
const UNCHECKED_DESCRIPTION =
    "This workflow is not currently bookmarked, click this link to add a bookmark for this workflow.";
const BOOKMARKS_DESCRIPTION = "Workflows that are bookmarked will appear in your Galaxy tool panel for quick access.";

export default {
    components: {
        BLink,
        FontAwesomeIcon,
    },
    directives: {
        VBTooltip,
    },
    props: {
        checked: {
            type: Boolean,
            required: true,
        },
    },
    computed: {
        title() {
            if (this.checked) {
                return `${CHECKED_DESCRIPTION} ${BOOKMARKS_DESCRIPTION}`;
            } else {
                return `${UNCHECKED_DESCRIPTION} ${BOOKMARKS_DESCRIPTION}`;
            }
        },
    },
    methods: {
        onClick() {
            this.$emit("bookmark", !this.checked);
        },
    },
};
</script>
