<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { type ConcreteObjectStoreModel } from "@/api";
import { useStorageLocationConfiguration } from "@/composables/storageLocation";
import { useObjectStoreStore } from "@/stores/objectStoreStore";
import localize from "@/utils/localization";

import DescribeObjectStore from "./DescribeObjectStore.vue";
import ObjectStoreSelectButton from "./ObjectStoreSelectButton.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface SelectObjectStoreProps {
    selectedObjectStoreId?: string | null;
    defaultOptionTitle: string;
    defaultOptionDescription: string;
    forWhat: string;
    parentError?: string | null;
}

const props = withDefaults(defineProps<SelectObjectStoreProps>(), {
    selectedObjectStoreId: null,
    parentError: null,
});

const store = useObjectStoreStore();
const { loading, loadErrorMessage, selectableObjectStores } = storeToRefs(store);
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

const loadingObjectStoreInfoMessage = ref("Loading storage location information");
const whyIsSelectionPreferredText = ref(`
Select a preferred storage location for new datasets. Depending on the job and workflow execution configuration of
this Galaxy a different storage location may be ultimately used. After a dataset is created,
click on the info icon in the history panel to view information about where it is stored. If it
is not stored in the place you want, contact Galaxy administrator for more information.
`);

function variant(objectStoreId?: string | null) {
    if (props.selectedObjectStoreId == objectStoreId) {
        return "info";
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

const selectedObjectStore = computed(() => {
    if (props.selectedObjectStoreId) {
        const objectStore = store.objectStoresById[props.selectedObjectStoreId];
        return objectStore ?? null;
    } else {
        return null;
    }
});
</script>

<template>
    <LoadingSpan v-if="loading" :message="loadingObjectStoreInfoMessage" />
    <div v-else>
        <b-alert v-if="error" variant="danger" class="object-store-selection-error" show>
            {{ error }}
        </b-alert>

        <p v-if="isOnlyPreference" v-localize>
            {{ whyIsSelectionPreferredText }}
        </p>

        <div class="object-store-selection-columns">
            <b-button-group vertical size="lg" style="width: 100%">
                <b-button
                    id="no-preferred-object-store-button"
                    :variant="variant(null)"
                    class="preferred-object-store-select-button"
                    data-object-store-id="__null__"
                    @click="handleSubmit(null)">
                    <i>{{ localize(defaultOptionTitle) }}</i>
                </b-button>
                <ObjectStoreSelectButton
                    v-for="objectStore in selectableAndVisibleObjectStores"
                    :key="objectStore.object_store_id"
                    id-prefix="preferred"
                    :object-store="objectStore"
                    :variant="variant(objectStore.object_store_id)"
                    class="preferred-object-store-select-button"
                    @click="handleSubmit(objectStore)" />
            </b-button-group>

            <span v-if="!selectedObjectStoreId" v-localize> {{ defaultOptionDescription }} </span>
            <DescribeObjectStore v-else-if="selectedObjectStore" :what="forWhat" :storage-info="selectedObjectStore" />
        </div>
    </div>
</template>

<style lang="scss" scoped>
.object-store-selection-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}
</style>
