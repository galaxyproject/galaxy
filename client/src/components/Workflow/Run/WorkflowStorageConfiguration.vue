<script setup lang="ts">
import { faHdd } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useConfigStore } from "@/stores/configurationStore";

import WorkflowSelectPreferredObjectStore from "./WorkflowSelectPreferredObjectStore.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import WorkflowTargetPreferredObjectStorePopover from "@/components/Workflow/Run/WorkflowTargetPreferredObjectStorePopover.vue";

interface Props {
    splitObjectStore: boolean;
    invocationPreferredObjectStoreId?: string | null;
    invocationPreferredIntermediateObjectStoreId?: string | null;
}

const props = withDefaults(defineProps<Props>(), {
    invocationPreferredObjectStoreId: null,
    invocationPreferredIntermediateObjectStoreId: null,
});

const emit = defineEmits<{
    (e: "updated", preferredObjectStoreId: string | null, intermediate: boolean): void;
}>();

const showPreferredObjectStoreModal = ref(false);
const showIntermediatePreferredObjectStoreModal = ref(false);
const selectedObjectStoreId = ref(props.invocationPreferredObjectStoreId);
const selectedIntermediateObjectStoreId = ref(props.invocationPreferredIntermediateObjectStoreId);

const { config } = storeToRefs(useConfigStore());

const preferredOrEmptyString = computed(() => {
    if (config.value?.object_store_always_respect_user_selection) {
        return "";
    } else {
        return "Preferred";
    }
});

const primaryModalTitle = computed(() => `Invocation ${preferredOrEmptyString.value} Galaxy Storage`);

const intermediateModalTitle = computed(
    () => `Invocation ${preferredOrEmptyString.value} Galaxy Storage (Intermediate Datasets)`,
);

const suffixPrimary = computed(() => {
    if (props.splitObjectStore) {
        return ` (Workflow Output Datasets)`;
    } else {
        return "";
    }
});

function onUpdate(preferredObjectStoreId: string | null) {
    selectedObjectStoreId.value = preferredObjectStoreId;
    emit("updated", preferredObjectStoreId, false);
}

function onUpdateIntermediate(preferredObjectStoreId: string | null) {
    selectedIntermediateObjectStoreId.value = preferredObjectStoreId;
    emit("updated", preferredObjectStoreId, true);
}
</script>

<template>
    <span class="workflow-storage-indicators">
        <GButton
            id="workflow-storage-indicator-primary"
            class="workflow-storage-indicator workflow-storage-indicator-primary"
            transparent
            color="blue"
            @click="showPreferredObjectStoreModal = true">
            <FontAwesomeIcon :icon="faHdd" />
            Primary Storage
        </GButton>
        <WorkflowTargetPreferredObjectStorePopover
            target="workflow-storage-indicator-primary"
            :title-suffix="suffixPrimary"
            :invocation-preferred-object-store-id="selectedObjectStoreId || undefined">
        </WorkflowTargetPreferredObjectStorePopover>
        <GModal :show.sync="showPreferredObjectStoreModal" :title="primaryModalTitle" size="small" fixed-height>
            <WorkflowSelectPreferredObjectStore
                :invocation-preferred-object-store-id="selectedObjectStoreId"
                @updated="onUpdate" />
        </GModal>
        <GButton
            v-if="splitObjectStore"
            id="workflow-storage-indicator-intermediate"
            class="workflow-storage-indicator workflow-storage-indicator-intermediate"
            transparent
            color="blue"
            @click="showIntermediatePreferredObjectStoreModal = true">
            <FontAwesomeIcon :icon="faHdd" />
            Intermediate Storage
        </GButton>
        <WorkflowTargetPreferredObjectStorePopover
            v-if="splitObjectStore"
            target="workflow-storage-indicator-intermediate"
            title-suffix=" (Intermediate Datasets)"
            :invocation-preferred-object-store-id="selectedIntermediateObjectStoreId || undefined">
        </WorkflowTargetPreferredObjectStorePopover>
        <GModal
            :show.sync="showIntermediatePreferredObjectStoreModal"
            :title="intermediateModalTitle"
            size="small"
            fixed-height>
            <WorkflowSelectPreferredObjectStore
                :invocation-preferred-object-store-id="selectedIntermediateObjectStoreId"
                @updated="onUpdateIntermediate" />
        </GModal>
    </span>
</template>
