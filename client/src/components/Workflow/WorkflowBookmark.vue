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

const CHECKED_DESCRIPTION = "Remove bookmark";
const UNCHECKED_DESCRIPTION = "Add a bookmark. This workflow will appear in the left tool panel.";

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
