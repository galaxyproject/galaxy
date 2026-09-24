<script setup lang="ts">
import { faDatabase } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import Multiselect from "vue-multiselect";

import { useTargetObjectStoreUploadState } from "@/composables/upload/useTargetObjectStoreUploadState";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";

interface Props {
    targetObjectStoreId: string | null;
    targetHistoryId: string;
    storeCaption?: string;
    changeLinkTooltip?: string;
    disabled?: boolean;
    disabledMessage?: string | null;
}

const props = withDefaults(defineProps<Props>(), {
    storeCaption: "Target storage",
    changeLinkTooltip: "Change target storage location",
    disabled: false,
    disabledMessage: null,
});

const emit = defineEmits<{
    (e: "select-store", selection: { object_store_id: string | null; private: boolean }): void;
}>();

const objectStoreStore = useObjectStoreStore();
const { selectableObjectStores } = storeToRefs(objectStoreStore);

type SelectorOption = {
    id: string;
    name: string;
    description: string;
    object_store_id: string | null;
    private: boolean;
    badges: unknown[];
};

const defaultStoreOption: SelectorOption = {
    id: "__null__",
    name: "Use history preference",
    description: "Uploads will follow the selected history storage preference.",
    object_store_id: null,
    private: false,
    badges: [],
};

const storeOptions = computed<SelectorOption[]>(() => {
    const stores = selectableObjectStores.value ?? [];
    const visibleStores = stores.filter(
        (store) => ("hidden" in store ? !store.hidden : true) && !!store.object_store_id,
    );
    return [
        defaultStoreOption,
        ...visibleStores.map((store) => {
            const objectStoreId = store.object_store_id as string;
            return {
                id: objectStoreId,
                name: store.name ?? "Unknown storage location",
                description: store.description ?? "",
                object_store_id: objectStoreId,
                private: store.private,
                badges: store.badges ?? [],
            };
        }),
    ];
});

const canChangeStore = computed(() => storeOptions.value.length > 1 && !props.disabled);

const currentStoreOption = computed<SelectorOption>(() => {
    return (
        storeOptions.value.find((option) => option.object_store_id === props.targetObjectStoreId) ?? defaultStoreOption
    );
});

const { warningMessage } = useTargetObjectStoreUploadState(
    computed(() => props.targetObjectStoreId),
    computed(() => props.targetHistoryId),
);

function handleStoreSelected(selectedOption: SelectorOption | null) {
    if (!selectedOption) {
        return;
    }
    emit("select-store", {
        object_store_id: selectedOption.object_store_id,
        private: selectedOption.private,
    });
}
</script>

<template>
    <div>
        <div class="d-flex align-items-center flex-nowrap w-100">
            <span class="d-flex align-items-center text-nowrap flex-shrink-0">
                <span v-g-tooltip.hover title="The storage location where these datasets will be uploaded.">
                    <FontAwesomeIcon class="mr-1" :icon="faDatabase" />{{ storeCaption }}:
                </span>
            </span>
            <div
                v-g-tooltip.hover
                class="flex-grow-1 ml-2"
                data-test-id="upload-target-object-store-selector"
                :title="disabledMessage ?? changeLinkTooltip">
                <Multiselect
                    :value="currentStoreOption"
                    :options="storeOptions"
                    :allow-empty="false"
                    :searchable="false"
                    :show-labels="false"
                    :disabled="!canChangeStore"
                    class="w-100 target-object-store-multiselect multiselect--soft-option-highlight"
                    label="name"
                    track-by="id"
                    @input="handleStoreSelected">
                    <template v-slot:singleLabel="{ option }">
                        <span class="d-flex align-items-center justify-content-between">
                            <span class="text-truncate mr-2">{{ option.name ?? "Unknown storage location" }}</span>
                            <ObjectStoreBadges :badges="option.badges" size="lg" class="flex-shrink-0" />
                        </span>
                    </template>
                    <template v-slot:option="{ option }">
                        <div
                            data-test-id="target-object-store-option"
                            :data-id="option.id"
                            class="w-100 text-wrap py-1">
                            <div class="d-flex align-items-start justify-content-between">
                                <span class="font-weight-bold">{{ option.name ?? "Unknown storage location" }}</span>
                                <ObjectStoreBadges :badges="option.badges" size="lg" class="ml-2 flex-shrink-0" />
                            </div>
                            <div v-if="option.description" class="small text-muted mt-1 text-break">
                                {{ option.description }}
                            </div>
                        </div>
                    </template>
                </Multiselect>
            </div>
        </div>

        <GAlert v-if="warningMessage" show variant="warning" class="mb-2 py-1">
            {{ warningMessage }}
        </GAlert>
    </div>
</template>
