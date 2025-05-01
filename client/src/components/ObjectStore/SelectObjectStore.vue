<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { type ConcreteObjectStoreModel } from "@/api";
import { useStorageLocationConfiguration } from "@/composables/storageLocation";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

import ObjectStoreSelectButton from "./ObjectStoreSelectButton.vue";
import ObjectStoreSelectButtonDescribePopover from "./ObjectStoreSelectButtonDescribePopover.vue";
import ObjectStoreSelectButtonPopover from "./ObjectStoreSelectButtonPopover.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface SelectObjectStoreProps {
    selectedObjectStoreId?: String | null;
    defaultOptionTitle: string;
    defaultOptionDescription: String;
    forWhat: string;
    parentError?: String | null;
}

const props = defineProps<SelectObjectStoreProps>();

const store = useObjectStoreStore();
const { isLoading, loadErrorMessage, selectableObjectStores } = storeToRefs(store);
const { isOnlyPreference } = useStorageLocationConfiguration();

const selectableAndVisibleObjectStores = computed(() => {
    const allSelectableObjectStores = selectableObjectStores.value;
    if (allSelectableObjectStores != null) {
        return allSelectableObjectStores.filter((item) => {
            return "hidden" in item ? !item.hidden : true;
        });
    } else {
        return [];
    }
});
const loadingObjectStoreInfoMessage = ref("正在加载存储位置信息");
const whyIsSelectionPreferredText = ref(`
为新的数据集选择首选存储位置。根据此Galaxy的作业和工作流执行配置，
最终可能会使用不同的存储位置。创建数据集后，
点击历史面板中的信息图标，查看其存储位置的相关信息。如果
数据集未存储在您期望的位置，请联系Galaxy管理员获取更多信息。
`);

function variant(objectStoreId: string | null) {
    if (props.selectedObjectStoreId == objectStoreId) {
        return "outline-primary";
    } else {
        return "outline-info";
    }
}

const emit = defineEmits<{
    (e: "onSubmit", id: string | null, isPrivate: boolean): void;
}>();

const error = computed(() => {
    return props.parentError || loadErrorMessage.value;
});

async function handleSubmit(preferredObjectStore: ConcreteObjectStoreModel | null) {
    const id: string | null = (preferredObjectStore ? preferredObjectStore.object_store_id : null) as string | null;
    const isPrivate: boolean = preferredObjectStore ? preferredObjectStore.private : false;
    emit("onSubmit", id, isPrivate);
}
</script>

<template>
    <div>
        <LoadingSpan v-if="isLoading" :message="loadingObjectStoreInfoMessage" />
        <div v-else>
            <b-alert v-if="error" variant="danger" class="object-store-selection-error" show>
                {{ error }}
            </b-alert>
            <b-row align-h="center">
                <b-col cols="7">
                    <b-button-group vertical size="lg" style="width: 100%">
                        <b-button
                            id="no-preferred-object-store-button"
                            :variant="variant(null)"
                            class="preferred-object-store-select-button"
                            data-object-store-id="__null__"
                            @click="handleSubmit(null)"
                            ><i v-localize>{{ defaultOptionTitle }}</i></b-button
                        >
                        <ObjectStoreSelectButton
                            v-for="objectStore in selectableAndVisibleObjectStores"
                            :key="objectStore.object_store_id"
                            id-prefix="preferred"
                            :object-store="objectStore"
                            :variant="variant(objectStore.object_store_id ?? null)"
                            class="preferred-object-store-select-button"
                            @click="handleSubmit(objectStore)" />
                    </b-button-group>
                </b-col>
                <b-col v-if="isOnlyPreference" cols="5">
                    <p v-localize style="float: right">
                        {{ whyIsSelectionPreferredText }}
                    </p>
                </b-col>
            </b-row>
            <ObjectStoreSelectButtonPopover target="no-preferred-object-store-button" :title="defaultOptionTitle">
                <span v-localize>{{ defaultOptionDescription }}</span>
            </ObjectStoreSelectButtonPopover>
            <ObjectStoreSelectButtonDescribePopover
                v-for="objectStore in selectableAndVisibleObjectStores"
                :key="objectStore.object_store_id"
                id-prefix="preferred"
                :what="forWhat"
                :object-store="objectStore">
            </ObjectStoreSelectButtonDescribePopover>
        </div>
    </div>
</template>
