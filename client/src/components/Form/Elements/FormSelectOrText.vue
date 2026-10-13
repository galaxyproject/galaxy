<script setup lang="ts">
import { BFormInput } from "bootstrap-vue";
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { uid } from "@/utils/utils";

import FormSelect from "@/components/Form/Elements/FormSelect.vue";

// The select holds generated values rather than the options' own, so no option value can collide with
// "Other..." and a null-valued option stays distinct from the null FormSelect emits on deselect.
const OTHER_VALUE = "other";

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
         * Returns an error for text that must not be saved. Blank text is never saved. This is a client-side
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
// an empty text field the user hasn't typed in yet is waiting for a value, so it isn't marked invalid
const edited = ref(false);

function optionValue(index: number) {
    return `option-${index}`;
}

const selectOptions = computed(() => [
    ...props.options.map((option, index) => ({ label: option.label, value: optionValue(index) })),
    { label: props.otherLabel, value: OTHER_VALUE },
]);
const selectedIndex = computed(() =>
    otherMode.value ? -1 : props.options.findIndex((option) => option.value === (props.value ?? null)),
);
const selectValue = computed(() => {
    if (otherMode.value) {
        return OTHER_VALUE;
    }
    return selectedIndex.value >= 0 ? optionValue(selectedIndex.value) : null;
});
const selectedHelp = computed(() => props.options[selectedIndex.value]?.help);

const textError = computed(() => {
    if (!otherMode.value) {
        return undefined;
    }
    return props.validate?.(text.value) ?? (text.value.trim() ? undefined : "Enter a value.");
});

const textInvalid = computed(() => Boolean(textError.value) && (edited.value || Boolean(text.value)));

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
        edited.value = false;
        otherMode.value = value !== null && !isListed(value);
    },
    { immediate: true },
);

watch(
    () => props.options,
    () => {
        // a selected value the options no longer list moves to the text field rather than blanking the select
        if (!otherMode.value && props.value !== null && !isListed(props.value)) {
            text.value = props.value;
            edited.value = false;
            otherMode.value = true;
        }
    },
);

function onSelect(value: string | null) {
    if (value === null) {
        // deselecting the current option
        return;
    }
    if (value === OTHER_VALUE) {
        otherMode.value = true;
        text.value = props.value ?? "";
        edited.value = false;
        return;
    }
    const selected = props.options[selectOptions.value.findIndex((option) => option.value === value)]!.value;
    otherMode.value = false;
    text.value = selected ?? "";
    emit("input", selected);
}

function onText(value: string) {
    text.value = value;
    edited.value = true;
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
                :state="textInvalid ? false : null"
                :placeholder="otherPlaceholder"
                :aria-label="otherLabel"
                @input="onText" />
            <small v-if="otherHelp" class="form-text text-muted">{{ otherHelp }}</small>
        </div>
    </div>
</template>

<style scoped>
/* option labels are words, so wrap them between words rather than anywhere as other selects do */
.form-select-or-text :deep(.multiselect__tags .multiselect__single) {
    word-break: normal;
    overflow-wrap: anywhere;
}
</style>
