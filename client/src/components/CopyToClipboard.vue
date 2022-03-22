<template>
    <font-awesome-icon class="cursor-pointer" :title="title" :icon="['far', 'copy']" @click="copy(text, message)" />
</template>

<script>
import { copy } from "utils/clipboard";
import { faCopy } from "@fortawesome/free-regular-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

library.add(faCopy);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        text: {
            type: String,
            required: true,
        },
        message: {
            type: String,
            required: true,
        },
        title: {
            type: String,
            default: "copy to clipboard",
            required: false,
        },
    },
    methods: {
        copy(text, message) {
            copy(text, message);
        },
    },
};
</script>
