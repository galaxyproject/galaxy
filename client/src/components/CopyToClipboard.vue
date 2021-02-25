<template>
    <font-awesome-icon title="Copy Tool ID" icon="copy" @click="copy(text, message)"></font-awesome-icon>
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
    },
    methods: {
        copy(text, message) {
            copy(text, message);
        },
    },
};
</script>
