<!-- https://schema.org/isBasedOn -->
<script setup lang="ts">
import { BFormInput } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { BasedOnWork, Creator } from "@/api/workflows";

import CreatorEditor from "./CreatorEditor.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

const props = defineProps<{
    work: BasedOnWork;
}>();

const emit = defineEmits<{
    (e: "onSave", work: BasedOnWork): void;
    (e: "onReset"): void;
}>();

const ATTRIBUTES = [
    { key: "url", label: "URL", placeholder: "e.g. https://github.com/nf-core/rnaseq", type: "url" },
    { key: "version", label: "Version", placeholder: "e.g. 3.14.0", type: "text" },
    {
        key: "identifier",
        label: "Identifier",
        placeholder: "e.g. https://doi.org/10.5281/zenodo.1400710",
        type: "text",
    },
    { key: "license", label: "License", placeholder: "SPDX identifier, e.g. MIT", type: "text" },
] as const;

type TextAttribute = "name" | (typeof ATTRIBUTES)[number]["key"];

const values = ref<Record<TextAttribute, string>>({
    name: props.work.name ?? "",
    url: props.work.url ?? "",
    version: props.work.version ?? "",
    identifier: props.work.identifier ?? "",
    license: props.work.license ?? "",
});
// CreatorEditor pushes new entries onto the array it is given, so hand it a copy.
const creators = ref<Creator[]>([...(props.work.creator ?? [])]);
const nameMissing = ref(false);

const nameState = computed(() => (nameMissing.value ? false : null));

function onCreators(newCreators: Creator[]) {
    creators.value = newCreators;
}

function onSave() {
    if (!values.value.name.trim()) {
        nameMissing.value = true;
        return;
    }
    // Keep attributes this form does not edit (e.g. description) and drop emptied ones.
    const work: BasedOnWork = { ...props.work, class: props.work.class || "SoftwareSourceCode" };
    for (const [key, value] of Object.entries(values.value) as [TextAttribute, string][]) {
        if (value.trim()) {
            work[key] = value.trim();
        } else {
            delete work[key];
        }
    }
    if (creators.value.length) {
        work.creator = creators.value;
    } else {
        delete work.creator;
    }
    emit("onSave", work);
}
</script>

<template>
    <!-- Not a <form>: CreatorEditor nests its own person/organization forms. -->
    <div class="based-on-form">
        <div role="group" class="form-group">
            <label for="based-on-name">Name</label>
            <BFormInput
                id="based-on-name"
                v-model="values.name"
                placeholder="e.g. nf-core/rnaseq"
                :state="nameState"
                @focus="nameMissing = false" />
            <div v-if="nameMissing" class="error">Please provide a name</div>
        </div>
        <div v-for="attribute in ATTRIBUTES" :key="attribute.key" role="group" class="form-group">
            <label :for="`based-on-${attribute.key}`">{{ attribute.label }}</label>
            <BFormInput
                :id="`based-on-${attribute.key}`"
                v-model="values[attribute.key]"
                :type="attribute.type"
                :placeholder="attribute.placeholder" />
        </div>
        <div role="group" class="form-group">
            <label>Upstream creators</label>
            <CreatorEditor :creators="creators" @onCreators="onCreators" />
        </div>
        <GButton id="based-on-save" color="blue" @click="onSave">Save</GButton>
        <GButton id="based-on-cancel" color="red" @click="emit('onReset')">Cancel</GButton>
    </div>
</template>

<style lang="scss" scoped>
.error {
    color: var(--color-red-500);
}
</style>
