<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItemButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useUserFlagsStore } from "@/stores/userFlagsStore";

import FormCheck from "@/components/Form/Elements/FormCheck.vue";
import FormRadio from "@/components/Form/Elements/FormRadio.vue";
import FormSelect from "@/components/Form/Elements/FormSelect.vue";
import FormSelectMany from "@/components/Form/Elements/FormSelectMany/FormSelectMany.vue";

library.add(faCaretDown);

interface Props {
    display?: string;
    optional?: boolean;
    multiple?: boolean;
    value?: string | string[] | number | number[];
    options?: [string, string | number][];
    data?: {
        label: string;
        value: string;
    }[];
}

const props = withDefaults(defineProps<Props>(), {
    display: undefined,
    optional: false,
    multiple: false,
    value: undefined,
    options: undefined,
    data: undefined,
});

const emit = defineEmits<{
    (e: "input", value: string | string[] | number | number[]): void;
}>();

const { preferredFormSelectElement } = storeToRefs(useUserFlagsStore());

const useMany = ref(false);

const currentValue = computed({
    get: () => {
        return props.value;
    },
    set: (val) => {
        emit("input", val);
    },
});

/** Provides formatted select options. */
const currentOptions = computed(() => {
    const data = props.data;
    const options = props.options;

    let result: { label: string; value?: string | number }[] = [];

    if (options && options.length > 0) {
        result = options.map((option) => ({ label: option[0], value: option[1] }));
    } else if (data && data.length > 0) {
        result = data;
    }

    if (!props.display && !props.multiple && props.optional) {
        result.unshift({
            label: "Nothing selected",
            value: undefined,
        });
    }

    return result;
});

watch(
    () => preferredFormSelectElement.value,
    (newValue, oldValue) => {
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
    { immediate: true }
);

const showSelectPreference = computed(
    () => props.multiple && props.display !== "checkboxes" && props.display !== "radio"
);

const displayMany = computed(() => showSelectPreference.value && useMany.value);
const showManyButton = computed(() => showSelectPreference.value && !useMany.value);
const showMultiButton = computed(() => displayMany.value);
</script>

<template>
    <div>
        <FormCheck v-if="display === 'checkboxes'" v-model="currentValue" :options="currentOptions" />
        <FormRadio v-else-if="display === 'radio'" v-model="currentValue" :options="currentOptions" />
        <FormSelectMany v-else-if="displayMany" v-model="currentValue" :options="currentOptions" />
        <FormSelect v-else v-model="currentValue" :multiple="multiple" :optional="optional" :options="currentOptions" />

        <div v-if="showSelectPreference" class="d-flex">
            <button v-if="showManyButton" class="ui-link ml-1" @click="useMany = true">switch to column select</button>
            <button v-else-if="showMultiButton" class="ui-link ml-1" @click="useMany = false">
                switch to simple select
            </button>

            <BDropdown toggle-class="inline-icon-button d-block px-1" variant="link" no-caret>
                <template v-slot:button-content>
                    <FontAwesomeIcon :icon="faCaretDown" />

                    <span class="sr-only">select element preferences</span>
                </template>

                <BDropdownItemButton
                    :active="preferredFormSelectElement === 'none'"
                    @click="preferredFormSelectElement = 'none'">
                    No preference
                </BDropdownItemButton>

                <BDropdownItemButton
                    :active="preferredFormSelectElement === 'multi'"
                    @click="preferredFormSelectElement = 'multi'">
                    Default to simple select
                </BDropdownItemButton>

                <BDropdownItemButton
                    :active="preferredFormSelectElement === 'many'"
                    @click="preferredFormSelectElement = 'many'">
                    Default to column select
                </BDropdownItemButton>
            </BDropdown>
        </div>
    </div>
</template>
