<script setup lang="ts">
import { BFormGroup } from "bootstrap-vue";
import { ref, watch } from "vue";

import localize from "@/utils/localization";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";

interface Props {
    modelValue: string;
    shortWhatIsBeingCreated: string;
}

const props = defineProps<Props>();

const name = ref(props.modelValue);

const emit = defineEmits<{
    (e: "update:modelValue", value: string): void;
}>();

// Watch for external updates to modelValue and sync with innerValue
watch(
    () => props.modelValue,
    (newValue) => {
        name.value = newValue;
    },
);

watch(name, (newValue) => {
    emit("update:modelValue", newValue);
});

function updateName(v: string | null) {
    name.value = v ?? "";
}
</script>

<template>
    <BFormGroup
        class="flex-gapx-1 d-flex align-items-center w-50 inputs-form-group"
        :label="localize('Name:')"
        label-for="collection-name">
        <GFormInput
            id="collection-name"
            :model-value="name"
            class="collection-name"
            :placeholder="localize('Enter a name for your new ' + shortWhatIsBeingCreated)"
            size="small"
            required
            :state="!name ? false : null"
            @update:model-value="updateName" />
    </BFormGroup>
</template>
