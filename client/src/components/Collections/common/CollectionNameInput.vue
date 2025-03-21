<script setup lang="ts">
import { BFormGroup, BFormInput } from "bootstrap-vue";
import { ref, watch } from "vue";

import localize from "@/utils/localization";

interface Props {
    value: string;
    shortWhatIsBeingCreated: string;
}

const props = defineProps<Props>();

const name = ref(props.value);

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

// Watch for external updates to value and sync with innerValue
watch(
    () => props.value,
    (newValue) => {
        name.value = newValue;
    }
);

watch(name, (newValue) => {
    emit("input", newValue);
});
</script>

<template>
    <BFormGroup
        class="flex-gapx-1 d-flex align-items-center w-50 inputs-form-group"
        :label="localize('名称：')"
        label-for="collection-name">
        <BFormInput
            id="collection-name"
            v-model="name"
            class="collection-name"
            :placeholder="localize('请输入您的新' + shortWhatIsBeingCreated + '的名称')"
            size="sm"
            required
            :state="!name ? false : null" />
    </BFormGroup>
</template>
