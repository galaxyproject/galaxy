<script setup lang="ts">
import { ref } from "vue";

import SelectObjectStore from "@/components/ObjectStore/SelectObjectStore.vue";

interface ToolSelectProps {
    toolPreferredObjectStoreId?: String | null;
}

const props = withDefaults(defineProps<ToolSelectProps>(), {
    toolPreferredObjectStoreId: null,
});

const selectedObjectStoreId = ref<String | null>(props.toolPreferredObjectStoreId);
const newDatasetsDescription = "The default storage location for the outputs of this tool";
const defaultOptionTitle = "Use Defaults";
const defaultOptionDescription =
    "If the history has a default set, that will be used. If instead, you've set an option in your user preferences - that will be assumed to be your default selection. Finally, the Galaxy configuration will be used.";

const emit = defineEmits<{
    (e: "updated", id: string | null): void;
}>();

async function handleSubmit(preferredObjectStoreId: string | null) {
    selectedObjectStoreId.value = preferredObjectStoreId;
    emit("updated", preferredObjectStoreId);
}
</script>

<template>
    <SelectObjectStore
        :for-what="newDatasetsDescription"
        :selected-object-store-id="selectedObjectStoreId"
        :default-option-title="defaultOptionTitle"
        :default-option-description="defaultOptionDescription"
        @onSubmit="handleSubmit" />
</template>
