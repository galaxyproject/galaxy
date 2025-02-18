<script setup lang="ts">
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = defineProps({
    classes: {
        type: String,
        required: false,
        default: null,
    },
    message: {
        type: String,
        default: "Loading",
    },
    spinnerOnly: {
        type: Boolean,
        required: false,
        default: false,
    },
});
</script>

<template>
    <span>
        <FontAwesomeIcon :class="props.classes" :icon="faSpinner" spin title="loading" />
        <span v-if="!props.spinnerOnly" class="loading-message" data-description="loading message">
            {{ props.message }}.<span class="blinking">..</span>
        </span>
    </span>
</template>
