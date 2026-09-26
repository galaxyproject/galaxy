<script setup lang="ts">
import { faCopy } from "@fortawesome/free-regular-svg-icons";
import { faCheck, faEdit } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, nextTick, ref } from "vue";

import { copy } from "@/utils/clipboard";

import SlugInput from "./SlugInput.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

const props = defineProps<{
    prefix: string;
    slug: string;
}>();

const emit = defineEmits<{
    (e: "change", value: string): void;
    (e: "submit", value: string): void;
}>();

const editing = ref(false);

const slugInput = ref<InstanceType<typeof SlugInput>>();

const url = computed(() => props.prefix + props.slug);

async function onEdit() {
    editing.value = true;
    await nextTick();
    (slugInput.value?.$el as HTMLInputElement).focus();
}

function onChange(value: string) {
    emit("change", value);
}

function onSubmit() {
    editing.value = false;
    emit("submit", props.slug);
}

const copied = ref(false);
const clipboardTitle = computed(() => (copied.value ? "Copied!" : "Copy URL"));

function onCopy() {
    copy(url.value);
    copied.value = true;
}

function onCopyOut() {
    copied.value = false;
}
</script>

<template>
    <div class="editable-url">
        url:
        <a v-if="!editing" id="item-url" :href="url" target="_top">{{ url }}</a>
        <span v-else id="item-url-text">
            {{ prefix }}
            <SlugInput
                ref="slugInput"
                class="ml-1"
                :slug="props.slug"
                @change="onChange"
                @cancel="onChange"
                @keyup.enter="onSubmit" />
        </span>

        <GButton
            v-if="!editing"
            v-g-tooltip.hover
            class="inline-icon-button"
            transparent
            icon-only
            color="blue"
            title="Edit URL"
            @click="onEdit">
            <FontAwesomeIcon :icon="faEdit" fixed-width />
        </GButton>
        <GButton
            v-else
            v-g-tooltip.hover
            class="inline-icon-button"
            transparent
            icon-only
            color="blue"
            title="Done"
            @click="onSubmit">
            <FontAwesomeIcon :icon="faCheck" fixed-width />
        </GButton>

        <GButton
            v-if="!editing"
            id="tooltip-clipboard"
            v-g-tooltip.hover
            :disabled="editing"
            class="inline-icon-button"
            transparent
            icon-only
            color="blue"
            :title="clipboardTitle"
            @click="onCopy"
            @mouseout="onCopyOut"
            @blur="onCopyOut">
            <FontAwesomeIcon :icon="faCopy" fixed-width />
        </GButton>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.editable-url {
    word-break: break-all;
}

.inline-icon-button:disabled:hover {
    background-color: $brand-secondary;
    color: unset;
}
</style>
