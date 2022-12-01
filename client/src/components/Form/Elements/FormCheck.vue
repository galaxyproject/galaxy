<script setup>
import { computed, ref } from "vue";

const $emit = defineEmits(["input"]);
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
        const val = props.value || [];
        return !Array.isArray(val) ? [val] : val;
    },
    set: (val) => {
        $emit("input", val);
    },
});

function onSelectAll() {
    if (selectAll.value) {
        const allValues = props.options.map((x) => x[1]);
        $emit("input", allValues)
    } else {
        $emit("input", []);
    }
}
</script>

<template>
    <div>
        <b-form-checkbox v-model="selectAll" @input="onSelectAll">{{ "Select/Unselect all" | l }}</b-form-checkbox>
        <b-form-checkbox-group v-model="currentValue" stacked>
            <b-form-checkbox 
                v-for="(option, index) in options" 
                :key="index" 
                :value="option[1]">
                    {{ option[0] }}
            </b-form-checkbox>
        </b-form-checkbox-group>
    </div>
</template>
