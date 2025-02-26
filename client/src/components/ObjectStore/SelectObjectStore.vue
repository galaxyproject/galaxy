<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { UserConcreteObjectStoreModel } from "@/api";
import { useStorageLocationConfiguration } from "@/composables/storageLocation";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

import SourceOptionCard from "@/components/ConfigTemplates/SourceOptionCard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";

interface SelectObjectStoreProps {
    selectedObjectStoreId?: String | null;
    defaultOptionTitle: string;
    defaultOptionDescription: string;
    forWhat: string;
    parentError?: String | null;
}

const props = defineProps<SelectObjectStoreProps>();

const { isOnlyPreference } = useStorageLocationConfiguration();
const store = useObjectStoreStore();
const { loading, loadErrorMessage, selectableObjectStores } = storeToRefs(store);

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

const emit = defineEmits<{
    (e: "onSubmit", id: string | null, isPrivate: boolean): void;
}>();

const error = computed(() => {
    return props.parentError || loadErrorMessage.value;
});

async function handleSubmit(preferredObjectStore: UserConcreteObjectStoreModel) {
    let id = preferredObjectStore?.object_store_id ?? null;
    const isPrivate: boolean = preferredObjectStore ? preferredObjectStore.private : false;

    if (id === "__null__") {
        id = null;
    }

    emit("onSubmit", id, isPrivate);
}

const defaultObjectStore: UserConcreteObjectStoreModel = {
    object_store_id: "__null__",
    name: props.defaultOptionTitle,
    description: props.defaultOptionDescription,
    badges: [],
    private: false,
    quota: { enabled: true, source: null },
    active: false,
    hidden: false,
    purged: false,
    secrets: [],
    template_id: "",
    template_version: 0,
    type: "disk",
    uuid: "",
    variables: null,
};
</script>

<template>
    <div>
        <LoadingSpan v-if="loading" message="Loading Galaxy storage information" />
        <div v-else>
            <span v-if="isOnlyPreference" v-localize>
                Select a preferred Galaxy storage for new datasets. Depending on the job and workflow execution
                configuration of this Galaxy a different Galaxy storage may be ultimately used. After a dataset is
                created, click on the info icon in the history panel to view information about where it is stored. If it
                is not stored in the place you want, contact Galaxy administrator for more information.
            </span>

            <BAlert v-if="error" variant="danger" class="object-store-selection-error" show>
                {{ error }}
            </BAlert>

            <div class="d-flex flex-wrap">
                <SourceOptionCard
                    :source-option="defaultObjectStore"
                    selection-mode
                    :selected="props.selectedObjectStoreId == null"
                    @select="handleSubmit(defaultObjectStore)" />

                <SourceOptionCard
                    v-for="objectStore in selectableAndVisibleObjectStores"
                    :key="objectStore.object_store_id"
                    :source-option="objectStore"
                    show-badges
                    selection-mode
                    submit-button-title="Select this storage location as the preferred storage location"
                    :selected="props.selectedObjectStoreId == objectStore.object_store_id"
                    @select="handleSubmit(objectStore)">
                    <template v-slot:badges>
                        <ObjectStoreBadges :badges="objectStore.badges" size="lg" />
                    </template>
                </SourceOptionCard>
            </div>
        </div>
    </div>
</template>
