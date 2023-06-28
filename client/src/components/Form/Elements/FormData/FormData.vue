<script setup lang="ts">
import FormSelect from "@/components/Form/Elements/FormSelect.vue";

const $emit = defineEmits(["input"]);

const props = withDefaults(
    defineProps<{
        multiple?: boolean;
        optional?: boolean;
        options: Array<[string, string]>;
        value?: Array<string> | string;
        extensions?: Array<string>;
        type?: string;
        flavor?: string;
        tag?: string;
    }>(),
    {
        multiple: false,
        optional: false,
        value: null,
        extensions: () => [],
        type: null,
        flavor: null,
        tag: null,
    }
);
</script>

<template>
    <div>placeholder</div>
</template>
