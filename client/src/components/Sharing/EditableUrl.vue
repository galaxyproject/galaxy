<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faCopy, faEdit } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, nextTick, ref } from "vue";

import { copy } from "@/utils/clipboard";

import SlugInput from "./SlugInput.vue";

library.add(faCopy, faEdit, faCheck);

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
const clipboardTitle = computed(() => (copied.value ? "已复制！" : "复制URL"));

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

        <BButton
            v-if="!editing"
            v-b-tooltip.hover
            class="inline-icon-button"
            title="Edit URL"
            size="md"
            @click="onEdit">
            <FontAwesomeIcon icon="edit" fixed-width />
        </BButton>
        <BButton v-else v-b-tooltip.hover class="inline-icon-button" title="Done" size="md" @click="onSubmit">
            <FontAwesomeIcon icon="check" fixed-width />
        </BButton>

        <BButton
            v-if="!editing"
            id="tooltip-clipboard"
            v-b-tooltip.hover
            :disabled="editing"
            size="md"
            class="inline-icon-button"
            :title="clipboardTitle"
            @click="onCopy"
            @mouseout="onCopyOut"
            @blur="onCopyOut">
            <FontAwesomeIcon :icon="['far', 'copy']" fixed-width />
        </BButton>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.editable-url {
    word-break: break-all;
}

.inline-icon-button:disabled:hover {
    background-color: $brand-secondary;
    color: unset;
}
</style>
