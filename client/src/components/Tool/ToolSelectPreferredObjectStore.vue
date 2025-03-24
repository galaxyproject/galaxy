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
const newDatasetsDescription = "此工具输出结果的默认存储位置";
const defaultOptionTitle = "使用默认值";
const defaultOptionDescription =
    "如果历史记录已设置默认值，将使用该默认值。如果您在用户首选项中设置了选项，则该选项将被视为您的默认选择。最后，将使用Galaxy配置。";

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
