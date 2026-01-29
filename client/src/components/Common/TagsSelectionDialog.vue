<script setup lang="ts">
import { computed, ref } from "vue";

import GModal from "@/components/BaseComponents/GModal.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

interface Props {
    show?: boolean;
    title?: string;
    initialTags?: string[];
}

const props = withDefaults(defineProps<Props>(), {
    title: "Select tags to add",
    initialTags: () => [],
});

const tags = ref(props.initialTags);

const emptyTagList = computed(() => {
    return tags.value.length === 0;
});

const emit = defineEmits<{
    (e: "cancel"): void;
    (e: "ok", tags: string[]): void;
}>();

function onTagsChange(newTags: string[]) {
    tags.value = newTags;
}

function onOk() {
    emit("ok", tags.value);
    resetTags();
}

function onCancel() {
    emit("cancel");
    resetTags();
}

function resetTags() {
    tags.value = props.initialTags;
}
</script>

<template>
    <GModal
        :show="show"
        ok-text="Add"
        :confirm="true"
        size="small"
        :title="title"
        :ok-disabled="emptyTagList"
        ok-disabled-title="Please select at least one tag"
        @ok="onOk"
        @cancel="onCancel">
        <StatelessTags :value="tags" @input="onTagsChange($event)" />
    </GModal>
</template>
