<template>
    <FontAwesomeIcon class="cursor-pointer" :title="title" :icon="['far', 'copy']" @click="copy(text, message)" />
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { copy } from "utils/clipboard";

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
            default: "复制到剪贴板",
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
