<script setup>
import { computed, ref } from "vue";

const emit = defineEmits(["input"]);
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

const indeterminate = computed(() => {
    const valueLength = currentValue.value.length;
    return valueLength !== 0 && valueLength !== props.options.length;
});

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
            size="sm"
            class="mb-1"
            :indeterminate="indeterminate"
            @input="onSelectAll">
            Select/Unselect all
        </b-form-checkbox>
        <b-form-checkbox-group v-model="currentValue" stacked>
            <b-form-checkbox v-for="(option, index) in options" :key="index" :value="option[1]">
                {{ option[0] }}
            </b-form-checkbox>
        </b-form-checkbox-group>
    </div>
    <b-alert v-else v-localize variant="warning" show> No options available. </b-alert>
</template>
