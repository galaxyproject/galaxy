<script setup lang="ts">
import { ref } from "vue";

import SelectObjectStore from "@/components/ObjectStore/SelectObjectStore.vue";

interface Props {
    invocationPreferredObjectStoreId?: String | null;
}

const props = withDefaults(defineProps<Props>(), {
    invocationPreferredObjectStoreId: null,
});

const emit = defineEmits<{
    (e: "updated", id: string | null): void;
}>();
const selectedObjectStoreId = ref<String | null>(props.invocationPreferredObjectStoreId);
const newDatasetsDescription = "此工作流程执行输出的默认存储位置";
const defaultOptionTitle = "使用默认设置";
const defaultOptionDescription =
    "如果历史记录已设置首选项，将使用该设置。如果您在用户首选项中设置了选项，则将使用该选项作为默认选择。最后，将使用 Galaxy 配置。";

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
