<script setup lang="ts">
import { computed } from "vue";

const props = defineProps({
    filter: { type: String, required: true },
    options: {
        type: Array<Object>,
        default: () => [
            { text: "Any", value: "any" },
            { text: "Yes", value: true },
            { text: "No", value: false },
        ],
    },
    settings: { type: Object, required: true },
});

const emit = defineEmits<{
    (e: "change", name: string, value: boolean | string | undefined): void;
}>();

const value = computed({
    get: () => {
        const value = props.settings[props.filter];
        return value !== undefined ? value : "any";
    },
    set: (newVal: boolean | string | undefined) => {
        const value = newVal !== null ? newVal : "any";
        emit("change", props.filter, value);
    },
});
</script>

<template>
    <b-form-group class="m-0">
        <b-form-radio-group
            v-model="value"
            :options="options"
            size="sm"
            buttons
            :data-description="`filter ${props.filter}`" />
    </b-form-group>
</template>
