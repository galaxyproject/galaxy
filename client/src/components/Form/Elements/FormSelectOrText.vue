<script setup lang="ts">
import { BFormInput } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { uid } from "@/utils/utils";

import FormSelect from "@/components/Form/Elements/FormSelect.vue";

const OTHER_VALUE = "__other__";

export interface SelectOrTextOption {
    label: string;
    value: string | null;
    /** Shown below the select while this option is selected. */
    help?: string;
}

const props = withDefaults(
    defineProps<{
        id?: string;
        value?: string | null;
        options: SelectOrTextOption[];
        /** Label of the option that switches to the text field. */
        otherLabel?: string;
        /** Shown below the text field. */
        otherHelp?: string;
        placeholder?: string;
        /** Returns an error for text that must not be saved. Empty text is never saved. */
        validate?: (text: string) => string | undefined;
    }>(),
    {
        id: () => `form-select-or-text-${uid()}`,
        value: null,
        otherLabel: "Other...",
        otherHelp: undefined,
        placeholder: undefined,
        validate: undefined,
    },
);

const emit = defineEmits<{
    (e: "input", value: string | null): void;
    (e: "alert", message: string | undefined): void;
}>();

const otherMode = ref(false);
const text = ref("");
let lastEmitted: string | null | undefined = undefined;

const selectOptions = computed(() => [...props.options, { label: props.otherLabel, value: OTHER_VALUE }]);
const selectValue = computed(() => (otherMode.value ? OTHER_VALUE : props.value || null));
const selectedHelp = computed(() =>
    otherMode.value ? undefined : props.options.find((option) => option.value === selectValue.value)?.help,
);

const textError = computed(() => {
    if (!otherMode.value) {
        return undefined;
    }
    return props.validate?.(text.value) ?? (text.value ? undefined : "Enter a value.");
});

watch(textError, (message) => emit("alert", message), { immediate: true });

function isListed(value: string | null): boolean {
    return props.options.some((option) => option.value === value);
}

watch(
    () => props.value,
    (value) => {
        if (value === lastEmitted) {
            // our own text echoed back - stay in the text field while typing through a listed value
            return;
        }
        text.value = value ?? "";
        otherMode.value = Boolean(value) && !isListed(value!);
    },
    { immediate: true },
);

function emitValue(value: string | null) {
    lastEmitted = value;
    emit("input", value);
}

function onSelect(value: string | null) {
    if (value === OTHER_VALUE) {
        otherMode.value = true;
        text.value = props.value ?? "";
        return;
    }
    otherMode.value = false;
    text.value = value ?? "";
    emitValue(value);
}

function onText(value: string) {
    text.value = value;
    if (!textError.value) {
        emitValue(value);
    }
}
</script>

<template>
    <div class="form-select-or-text">
        <FormSelect :id="id" :value="selectValue" :options="selectOptions" optional @input="onSelect" />
        <small v-if="selectedHelp" class="form-text text-muted">{{ selectedHelp }}</small>
        <div v-if="otherMode" class="mt-2">
            <BFormInput
                :id="`${id}-other`"
                :value="text"
                :state="textError ? false : null"
                :placeholder="placeholder"
                @input="onText" />
            <small v-if="otherHelp" class="form-text text-muted">{{ otherHelp }}</small>
        </div>
    </div>
</template>
