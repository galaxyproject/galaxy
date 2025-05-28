<script setup lang="ts">
import { ref } from "vue";

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

const emit = defineEmits<{
    (e: "cancel"): void;
    (e: "ok", tags: string[]): void;
}>();

function onTagsChange(newTags: string[]) {
    tags.value = newTags;
}
</script>

<template>
    <GModal :show="show" size="medium" :title="title" @ok="emit('ok', tags)" @cancel="emit('cancel')">
        <StatelessTags :value="tags" @input="onTagsChange($event)" />
    </GModal>
</template>
