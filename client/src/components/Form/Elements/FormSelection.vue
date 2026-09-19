<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, type PropType, ref, watch } from "vue";

import { useUserFlagsStore } from "@/stores/userFlagsStore";

import FormCheck from "./FormCheck.vue";
import FormRadio from "./FormRadio.vue";
import FormSelect from "./FormSelect.vue";
import FormSelectionPreference from "./FormSelectionPreference.vue";
import FormSelectMany from "./FormSelectMany/FormSelectMany.vue";

export interface SelectOption {
    label: string;
    value: any;
}

const emit = defineEmits<{
    (e: "input", value: any): void;
    (e: "search-change", query: string): void;
    (e: "preference-change", state: { showManyButton: boolean; showMultiButton: boolean }): void;
}>();

const props = defineProps({
    value: {
        type: null as unknown as PropType<any>,
        default: null,
    },
    data: {
        type: Array as PropType<SelectOption[] | null>,
        default: null,
    },
    display: {
        type: String,
        default: null,
    },
    optional: {
        type: Boolean,
        default: false,
    },
    options: {
        type: Array as PropType<any[] | null>,
        default: null,
    },
    multiple: {
        type: Boolean,
        default: false,
    },
    /**
     * Forwarded to ``FormSelectMany`` when the parent paginates options
     * server-side, so the column-select header reflects the backend's full
     * count of available items rather than just the locally-loaded slice.
     */
    totalEstimate: {
        type: Number as PropType<number | null>,
        default: null,
    },
    /**
     * When set, the simple/column select preference control is not rendered here.
     * The parent is expected to render it (see ``FormSelectionPreference``) using
     * the state exposed via ``preference-change`` and the exposed ``setUseMany``.
     */
    deferPreference: {
        type: Boolean,
        default: false,
    },
});

const currentValue = computed({
    get: () => {
        return props.value;
    },
    set: (val: any) => {
        emit("input", val);
    },
});

/** Provides formatted select options. */
const currentOptions = computed<SelectOption[]>(() => {
    const result: SelectOption[] = [];
    const data = props.data;
    const options = props.options;
    if (options && options.length > 0) {
        result.push(...options.map((option) => ({ label: option[0], value: option[1] })));
    } else if (data && data.length > 0) {
        result.push(...data);
    }
    if (!props.display && !props.multiple && props.optional) {
        result.unshift({
            label: "Nothing selected",
            value: null,
        });
    }
    return result;
});

const useMany = ref(false);

const { preferredFormSelectElement } = storeToRefs(useUserFlagsStore());

watch(
    () => preferredFormSelectElement.value,
    (newValue: string | undefined, oldValue: string | undefined) => {
        if (oldValue !== undefined) {
            return;
        }

        if (newValue === "none") {
            if (
                (Array.isArray(props.value) && props.value.length >= 15) ||
                (props.options && props.options.length >= 500)
            ) {
                useMany.value = true;
            } else {
                useMany.value = false;
            }
        } else if (newValue === "many") {
            useMany.value = true;
        } else {
            useMany.value = false;
        }
    },
    { immediate: true },
);

const showSelectPreference = computed(
    () => props.multiple && props.display !== "checkboxes" && props.display !== "radio" && props.display !== "simple",
);

const displayMany = computed(() => showSelectPreference.value && useMany.value);
const showManyButton = computed(() => showSelectPreference.value && !useMany.value);
const showMultiButton = computed(() => displayMany.value);

function setUseMany(value: boolean) {
    useMany.value = value;
}

// Keep the parent in sync when the preference control is rendered externally.
watch(
    [showManyButton, showMultiButton],
    ([many, multi]) => {
        if (props.deferPreference) {
            emit("preference-change", { showManyButton: many, showMultiButton: multi });
        }
    },
    { immediate: true },
);

defineExpose({
    displayMany,
    setUseMany,
});
</script>

<template>
    <div class="form-selection">
        <FormCheck v-if="display === 'checkboxes'" v-model="currentValue" :options="currentOptions" />
        <FormRadio v-else-if="display === 'radio'" v-model="currentValue" :options="currentOptions" />
        <FormSelectMany
            v-else-if="displayMany"
            v-model="currentValue"
            :options="currentOptions"
            :total-estimate="totalEstimate"
            @search-change="(q) => $emit('search-change', q)">
            <template v-slot:after-list>
                <slot name="after-list" />
            </template>
        </FormSelectMany>
        <FormSelect
            v-else
            v-model="currentValue"
            :multiple="multiple"
            :optional="optional"
            :options="currentOptions"
            @search-change="(q) => $emit('search-change', q)">
            <template v-slot:no-options>
                <slot name="no-options" />
            </template>
            <template v-slot:after-list>
                <slot name="after-list" />
            </template>
        </FormSelect>

        <FormSelectionPreference
            v-if="!deferPreference && showSelectPreference"
            :show-many-button="showManyButton"
            :show-multi-button="showMultiButton"
            @use-many="setUseMany" />
    </div>
</template>

<style scoped lang="scss">
.form-selection {
    &:deep(.alert) {
        margin-bottom: 0;
    }
}
</style>
