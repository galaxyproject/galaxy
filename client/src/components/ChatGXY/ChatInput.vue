<script setup lang="ts">
import { faPaperPlane } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import LoadingSpan from "@/components/LoadingSpan.vue";

const props = withDefaults(
    defineProps<{
        value: string;
        busy: boolean;
        placeholder?: string;
        disabled?: boolean;
    }>(),
    {
        placeholder: "Ask about tools, workflows, errors, or anything Galaxy...",
        disabled: false,
    },
);

const emit = defineEmits<{
    (e: "input", value: string): void;
    (e: "submit"): void;
}>();

function onInput(event: Event) {
    emit("input", (event.target as HTMLTextAreaElement).value);
}
</script>

<template>
    <div class="chat-input-container">
        <label for="chat-input" class="sr-only">Chat message</label>
        <textarea
            id="chat-input"
            :value="props.value"
            :disabled="busy || disabled"
            :placeholder="placeholder"
            rows="1"
            class="form-control chat-input"
            @input="onInput"
            @keydown.enter.prevent="!$event.shiftKey && emit('submit')" />
        <button
            :disabled="busy || disabled || !props.value.trim()"
            class="btn btn-primary send-button"
            @click="emit('submit')">
            <FontAwesomeIcon v-if="!busy" :icon="faPaperPlane" fixed-width />
            <LoadingSpan v-else message="" />
        </button>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.chat-input-container {
    display: flex;
    gap: 0.5rem;
    align-items: flex-end;

    .chat-input {
        flex: 1;
        resize: none;
        border-radius: $border-radius-base;
        padding: 0.625rem 0.875rem;
        border: $border-default;
        font-size: 0.9rem;
        min-height: 2.5rem;
        max-height: 8rem;

        &:focus {
            border-color: $brand-primary;
            box-shadow: 0 0 0 2px rgba($brand-primary, 0.1);
            outline: none;
        }
    }

    .send-button {
        flex-shrink: 0;
        border-radius: $border-radius-base;
        padding: 0.5rem 0.875rem;
    }
}

.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}
</style>
