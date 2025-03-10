<script setup lang="ts">
import { computed } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";

import FormElement from "@/components/Form/FormElement.vue";

const props = withDefaults(
    defineProps<{
        id: string;
        value?: string;
        title: string;
        help: string;
        datatypes: DatatypesMapperModel["datatypes"];
    }>(),
    {
        value: undefined,
    }
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
    extensions.unshift({
        0: "Leave unchanged",
        1: "",
    });
    return extensions;
});

function onChange(newDatatype: unknown) {
    emit("onChange", newDatatype);
}
</script>

<template>
    <FormElement
        :id="id"
        :value="value"
        :attributes="{ options: datatypeExtensions }"
        :title="title"
        type="select"
        :help="help"
        @input="onChange" />
</template>
