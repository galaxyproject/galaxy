<script setup lang="ts">
import FormSelect from "@/components/Form/Elements/FormSelect.vue";

const $emit = defineEmits(["input"]);

interface DataOption {
    id: string;
    keep: boolean;
    hid: string;
    name: string;
    src: string;
    tags: Array<string>;
}

interface DataOptions {
    hda: Array<[string, DataOption]>;
    hdca: Array<[string, DataOption]>;
}

const props = withDefaults(
    defineProps<{
        multiple?: boolean;
        optional?: boolean;
        options: DataOptions;
        value?: Array<DataOption>;
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
        type: "data",
        flavor: null,
        tag: null,
    }
);
</script>

<template>
    <div>placeholder</div>
</template>
