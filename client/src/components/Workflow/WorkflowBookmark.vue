<template>
    <GLink v-b-tooltip.hover :title="title" class="workflow-bookmark-link" @click="onClick">
        <FontAwesomeIcon v-if="checked" :icon="['fas', 'star']" />
        <FontAwesomeIcon v-else :icon="['far', 'star']" />
    </GLink>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import { faStar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { VBTooltip } from "bootstrap-vue";

import GLink from "@/component-library/GLink.vue";

library.add(faStar, farStar);

const CHECKED_DESCRIPTION = "Remove bookmark";
const UNCHECKED_DESCRIPTION = "Add a bookmark. This workflow will appear in the left tool panel.";

export default {
    components: {
        GLink,
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
            return this.checked ? CHECKED_DESCRIPTION : UNCHECKED_DESCRIPTION;
        },
    },
    methods: {
        onClick() {
            this.$emit("bookmark", !this.checked);
        },
    },
};
</script>
