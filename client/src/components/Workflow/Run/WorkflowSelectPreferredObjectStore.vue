<script setup lang="ts">
import SelectObjectStore from "@/components/ObjectStore/SelectObjectStore.vue";

interface Props {
    invocationPreferredObjectStoreId?: string | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "updated", id: string | null): void;
}>();

const newDatasetsDescription = "The default Galaxy storage for the outputs of this workflow invocation";
const defaultOptionTitle = "Use Defaults";
const defaultOptionDescription =
    "If the history has a preference set, that will be used. If instead, you've set an option in your user preferences - that will be assumed to be your default selection. Finally, the Galaxy configuration will be used.";

async function handleSubmit(preferredObjectStoreId: string | null) {
    emit("updated", preferredObjectStoreId);
}
</script>

<template>
    <SelectObjectStore
        :for-what="newDatasetsDescription"
        :selected-object-store-id="props.invocationPreferredObjectStoreId"
        :default-option-title="defaultOptionTitle"
        :default-option-description="defaultOptionDescription"
        @onSubmit="handleSubmit" />
</template>
