<script setup lang="ts">
import { BModal } from "bootstrap-vue";
import { ref } from "vue";

import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

interface Props {
    title?: string;
    initialTags?: string[];
}

const props = withDefaults(defineProps<Props>(), {
    title: "Select tags to add",
    initialTags: () => [],
});

const tags = ref(props.initialTags);

const emit = defineEmits<{
    (e: "cancel"): void;
    (e: "ok", tags: string[]): void;
}>();

function onTagsChange(newTags: string[]) {
    tags.value = newTags;
}
</script>

<template>
    <BModal visible centered size="lg" :title="title" @ok="emit('ok', tags)" @hide="emit('cancel')">
        <StatelessTags :value="tags" @input="onTagsChange($event)" />
    </BModal>
</template>
