<template>
    <FontAwesomeIcon class="cursor-pointer" :title="title" :icon="faCopy" @click="copy(text, message)" />
</template>

<script>
import { faCopy } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { copy } from "utils/clipboard";

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
    data() {
        return {
            faCopy,
        };
    },
    methods: {
        copy(text, message) {
            copy(text, message);
        },
    },
};
</script>
