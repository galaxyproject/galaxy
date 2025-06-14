<script setup lang="ts">
import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    value: string;
    title?: string;
    component?: string;
    noSaveOnBlur?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const clickToEditInput = ref<HTMLInputElement | null>(null);
const editable = ref(false);
const localValue = ref(props.value);

const computedValue = computed(() => props.value);

watch(
    () => editable.value,
    (value) => {
        if (!value) {
            emit("input", localValue.value);
        } else {
            setTimeout(() => {
                clickToEditInput.value?.focus();
            });
        }
    }
);

watch(
    () => props.value,
    (value) => {
        if (!editable.value) {
            localValue.value = value;
        }
    }
);

function onBlur(e: FocusEvent) {
    if (props.noSaveOnBlur) {
        const target = e.relatedTarget;
        // if the user clicked the save button, do nothing
        if (target instanceof HTMLElement && target.id === "save-btn") {
            return;
        } else {
            revertToOriginal();
        }
    } else {
        editable.value = false;
    }
}

function revertToOriginal() {
    localValue.value = props.value;
    editable.value = false;
}
</script>

<template>
    <div v-if="editable" class="d-flex flex-gapx-1">
        <BFormInput
            id="click-to-edit-input"
            ref="clickToEditInput"
            v-model="localValue"
            class="w-100"
            tabindex="0"
            contenteditable
            max-rows="4"
            @blur.prevent.stop="onBlur"
            @keyup.prevent.stop.enter="editable = false"
            @keyup.prevent.stop.escape="revertToOriginal"
            @click.prevent.stop />
        <GButton id="save-btn" class="p-0" transparent color="blue" size="small" @click.prevent.stop="editable = false">
            <FontAwesomeIcon :icon="faSave" />
            <span class="sr-only">Save changes</span>
        </GButton>
    </div>

    <component
        :is="props.component || 'label'"
        v-else
        role="button"
        for="click-to-edit-input"
        class="click-to-edit-label text-break"
        tabindex="0"
        @keyup.enter="editable = true"
        @click.stop="editable = true">
        <span v-if="computedValue">{{ computedValue }}</span>
        <i v-else>{{ title }}</i>
    </component>
</template>

<style scoped lang="scss">
.click-to-edit-label {
    cursor: text;
    &:hover > * {
        text-decoration: underline;
    }
}
</style>
