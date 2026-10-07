<script setup lang="ts">
import { BFormInput } from "bootstrap-vue";
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { uid } from "@/utils/utils";

import FormSelect from "@/components/Form/Elements/FormSelect.vue";

const OTHER_VALUE = "__other__";
// FormSelect emits null both for an option valued null and for deselecting the current option,
// so a null-valued option is held under this value instead and a null from FormSelect is ignored.
const NULL_VALUE = "__null__";

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
        otherPlaceholder?: string;
        /**
         * Returns an error for text that must not be saved. Empty text is never saved. This is a client-side
         * function, so only forms built in the client can set it.
         */
        validate?: (text: string) => string | undefined;
    }>(),
    {
        id: () => `form-select-or-text-${uid()}`,
        value: null,
        otherLabel: "Other...",
        otherHelp: undefined,
        otherPlaceholder: undefined,
        validate: undefined,
    },
);

const emit = defineEmits<{
    (e: "input", value: string | null): void;
    (e: "alert", message: string | undefined): void;
}>();

const otherMode = ref(false);
const text = ref("");

const selectOptions = computed(() => [
    ...props.options.map((option) => ({ ...option, value: option.value ?? NULL_VALUE })),
    { label: props.otherLabel, value: OTHER_VALUE },
]);
const selectValue = computed(() => (otherMode.value ? OTHER_VALUE : (props.value ?? NULL_VALUE)));
const selectedHelp = computed(() =>
    otherMode.value ? undefined : props.options.find((option) => option.value === (props.value ?? null))?.help,
);

const textError = computed(() => {
    if (!otherMode.value) {
        return undefined;
    }
    return props.validate?.(text.value) ?? (text.value ? undefined : "Enter a value.");
});

watch(textError, (message) => emit("alert", message), { immediate: true });
onBeforeUnmount(() => emit("alert", undefined));

function isListed(value: string | null): boolean {
    return props.options.some((option) => option.value === value);
}

watch(
    () => props.value,
    (value) => {
        if (otherMode.value && value === text.value) {
            // the typed text echoed back - stay in the text field while typing through a listed value
            return;
        }
        text.value = value ?? "";
        otherMode.value = Boolean(value) && !isListed(value!);
    },
    { immediate: true },
);

function onSelect(value: string | null) {
    if (value === null) {
        return;
    }
    if (value === OTHER_VALUE) {
        otherMode.value = true;
        text.value = props.value ?? "";
        return;
    }
    const selected = value === NULL_VALUE ? null : value;
    otherMode.value = false;
    text.value = selected ?? "";
    emit("input", selected);
}

function onText(value: string) {
    text.value = value;
    if (!textError.value) {
        emit("input", value);
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
                :placeholder="otherPlaceholder"
                :aria-label="otherLabel"
                @input="onText" />
            <small v-if="otherHelp" class="form-text text-muted">{{ otherHelp }}</small>
        </div>
    </div>
</template>
