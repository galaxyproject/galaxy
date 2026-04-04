<script setup lang="ts">
import { faPaperPlane } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import { detectMentionTrigger, type EntityType, type MentionTrigger } from "@/composables/useEntityMentions";

import MentionDropdown from "./MentionDropdown.vue";
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

const textareaEl = ref<HTMLTextAreaElement | null>(null);
const dropdownRef = ref<InstanceType<typeof MentionDropdown> | null>(null);
const mentionTrigger = ref<MentionTrigger | null>(null);

function onInput(event: Event) {
    const textarea = event.target as HTMLTextAreaElement;
    emit("input", textarea.value);
    updateMentionTrigger(textarea);
}

function updateMentionTrigger(textarea: HTMLTextAreaElement) {
    mentionTrigger.value = detectMentionTrigger(textarea.value, textarea.selectionStart);
}

const DROPDOWN_KEYS = new Set(["ArrowDown", "ArrowUp", "Tab", "Escape", "Enter"]);

function onKeydown(event: KeyboardEvent) {
    if (mentionTrigger.value && dropdownRef.value && DROPDOWN_KEYS.has(event.key)) {
        if (event.key !== "Enter" || !event.shiftKey) {
            dropdownRef.value.handleKeydown(event);
            return;
        }
    }

    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        emit("submit");
    }
}

function onMentionSelect(entityType: EntityType, identifier: string, displayText: string) {
    if (!mentionTrigger.value) {
        return;
    }

    const text = props.value;
    const start = mentionTrigger.value.startIndex;
    const end = mentionTrigger.value.endIndex;

    // If user picked an entity type (no identifier yet), replace partial with "@type:"
    // and keep the dropdown open for the entity list
    if (!identifier) {
        const newText = text.slice(0, start) + displayText + text.slice(end);
        emit("input", newText);

        // Set cursor after the inserted text
        const cursorPos = start + displayText.length;
        requestAnimationFrame(() => {
            if (textareaEl.value) {
                textareaEl.value.selectionStart = cursorPos;
                textareaEl.value.selectionEnd = cursorPos;
                updateMentionTrigger(textareaEl.value);
            }
        });
        return;
    }

    // Full mention selected — insert and add a trailing space
    const insertion = displayText + " ";
    const newText = text.slice(0, start) + insertion + text.slice(end);
    emit("input", newText);
    mentionTrigger.value = null;

    const cursorPos = start + insertion.length;
    requestAnimationFrame(() => {
        if (textareaEl.value) {
            textareaEl.value.selectionStart = cursorPos;
            textareaEl.value.selectionEnd = cursorPos;
            textareaEl.value.focus();
        }
    });
}

function closeMention() {
    mentionTrigger.value = null;
}
</script>

<template>
    <div class="chat-input-container">
        <label for="chat-input" class="sr-only">Chat message</label>
        <textarea
            id="chat-input"
            ref="textareaEl"
            :value="props.value"
            :disabled="busy || disabled"
            :placeholder="placeholder"
            rows="1"
            class="form-control chat-input"
            @input="onInput"
            @keydown="onKeydown" />
        <button
            :disabled="busy || disabled || !props.value.trim()"
            class="btn btn-primary send-button"
            @click="emit('submit')">
            <FontAwesomeIcon v-if="!busy" :icon="faPaperPlane" fixed-width />
            <LoadingSpan v-else message="" />
        </button>

        <MentionDropdown
            ref="dropdownRef"
            :visible="!!mentionTrigger"
            :mention-type="mentionTrigger?.entityType ?? null"
            :search-text="mentionTrigger?.searchText ?? ''"
            :anchor-el="textareaEl"
            @select="onMentionSelect"
            @close="closeMention" />
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.chat-input-container {
    display: flex;
    gap: 0.5rem;
    align-items: flex-end;
    position: relative;

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
            box-shadow: 0 0 0 2px rgba($brand-primary, 0.25);
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
