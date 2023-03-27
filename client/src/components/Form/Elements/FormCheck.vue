<script setup lang="ts">
import { computed, ref } from "vue";

export interface FormCheckProps {
    value?: string | string[];
    options: Array<[string, string]>;
}

const props = defineProps<FormCheckProps>();

const emit = defineEmits<{
    (e: "input", value: string[]): void;
}>();

const indeterminate = ref(false);

const currentValue = computed({
    get: () => {
        const val = props.value ?? [];
        return Array.isArray(val) ? val : [val];
    },
    set: (newValue) => {
        emit("input", newValue);

        if (newValue.length === 0) {
            selectAll.value = false;
            indeterminate.value = false;
        } else if (newValue.length === props.options.length) {
            selectAll.value = true;
            indeterminate.value = false;
        } else {
            indeterminate.value = true;
        }
    },
});

const hasOptions = computed(() => {
    return props.options.length > 0;
});

const selectAll = ref(false);

function onSelectAll() {
    if (selectAll.value) {
        const allValues = props.options.map((option) => option[1]);
        emit("input", allValues);
    } else {
        emit("input", []);
    }
}
</script>

<template>
    <div v-if="hasOptions">
        <b-form-checkbox
            v-model="selectAll"
            v-localize
            class="mb-1"
            :indeterminate="indeterminate"
            @input="onSelectAll">
            Select / Deselect all
        </b-form-checkbox>

        <b-form-checkbox-group v-model="currentValue" stacked class="pl-3">
            <b-form-checkbox v-for="(option, index) in options" :key="index" :value="option[1]">
                {{ option[0] }}
            </b-form-checkbox>
        </b-form-checkbox-group>
    </div>
    <b-alert v-else v-localize variant="warning" show> No options available. </b-alert>
</template>
