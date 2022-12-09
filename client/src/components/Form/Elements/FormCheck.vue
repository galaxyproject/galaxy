<script setup>
import { computed, ref, watch } from "vue";

const emit = defineEmits(["input", "indeterminate"]);
const props = defineProps({
    value: {
        default: null,
    },
    options: {
        type: Array,
        required: true,
    },
});
const selectAll = ref(false);
const indeterminate = ref(false);

const currentValue = computed({
    get: () => {
        const val = props.value ?? [];
        return Array.isArray(val) ? val : [val];
    },
    set: (val) => {
        emit("input", val);
    },
});

const hasOptions = computed(() => {
    return props.options.length > 0;
});

function onSelectAll() {
    if (selectAll.value) {
        const allValues = props.options.map((option) => option[1]);
        emit("input", allValues);
    } else {
        emit("input", []);
    }
}

watch(currentValue, () => {
    const valueLength = currentValue.value.length;
    if (valueLength === 0) {
        selectAll.value = false;
        indeterminate.value = false;
    } else if (valueLength === props.options.length) {
        selectAll.value = true;
        indeterminate.value = false;
    } else {
        indeterminate.value = true;
    }
});
</script>

<template>
    <div v-if="hasOptions">
        <b-form-checkbox
            v-model="selectAll"
            v-localize
            class="mb-1"
            :indeterminate="indeterminate"
            @input="onSelectAll"
            @change="emit('indeterminate', selectAll)">
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
