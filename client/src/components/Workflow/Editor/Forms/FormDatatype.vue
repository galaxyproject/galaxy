<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";

import FormElement from "@/components/Form/FormElement.vue";

const props = withDefaults(
    defineProps<{
        id: string;
        value?: string | string[];
        title: string;
        help: string;
        multiple?: boolean;
        datatypes: DatatypesMapperModel["datatypes"];
    }>(),
    {
        value: undefined,
        multiple: false,
    }
);

const currentValue = ref<string | string[] | undefined>(undefined);

watch(
    () => props.value,
    (newValue) => {
        currentValue.value = newValue;
    },
    { immediate: true }
);
const emit = defineEmits(["onChange"]);

const datatypeExtensions = computed(() => {
    const extensions = [];
    for (const key in props.datatypes) {
        extensions.push({ 0: props.datatypes[key] || "", 1: props.datatypes[key] || "" });
    }
    extensions.sort((a, b) => (a[0] > b[0] ? 1 : a[0] < b[0] ? -1 : 0));
    extensions.unshift({
        0: "Sequences",
        1: "Sequences",
    });
    extensions.unshift({
        0: "Roadmaps",
        1: "Roadmaps",
    });
    if (!props.multiple) {
        extensions.unshift({
            0: "Leave unchanged",
            1: "",
        });
    }
    return extensions;
});

function onInput(newDatatype: string) {
    currentValue.value = newDatatype;
    emit("onChange", currentValue.value);
}
</script>

<template>
    <FormElement
        :id="id"
        :value="currentValue"
        :attributes="{ options: datatypeExtensions, multiple: multiple, display: 'simple', optional: true }"
        :title="title"
        type="select"
        :help="help"
        @input="onInput" />
</template>
