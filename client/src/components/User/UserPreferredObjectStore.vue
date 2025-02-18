<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BModal, BRow } from "bootstrap-vue";
import { faHdd } from "font-awesome-6";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useConfigStore } from "@/stores/configurationStore";
import { prependPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import SelectObjectStore from "@/components/ObjectStore/SelectObjectStore.vue";

interface Props {
    preferredObjectStoreId?: string;
}

const { isLoaded: isConfigLoaded, config } = storeToRefs(useConfigStore());

const props = defineProps<Props>();

const error = ref();
const selectedObjectStoreId = ref(props.preferredObjectStoreId as string | null);

const title = computed(() => {
    return `${preferredOrEmptyString.value} Galaxy Storage`;
});
const preferredOrEmptyString = computed(() => {
    if (isConfigLoaded && config.value?.object_store_always_respect_user_selection) {
        return "";
    } else {
        return "Preferred";
    }
});

function resetModal() {
    error.value = null;
}

async function handleSubmit(preferred: string | null) {
    const payload = { preferred_object_store_id: preferred };
    const url = prependPath("api/users/current");

    try {
        await axios.put(url, payload);

        selectedObjectStoreId.value = preferred;
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
}
</script>

<template>
    <BModal
        id="modal-select-preferred-object-store"
        ref="modal"
        centered
        :title="title"
        :title-tag="titleTag"
        hide-footer
        static
        visible
        :size="modalSize"
        @hidden="resetModal">
        <SelectObjectStore
            :parent-error="error"
            :for-what="newDatasetsDescription"
            :selected-object-store-id="selectedObjectStoreId"
            :default-option-title="galaxySelectionDefaultTitle"
            :default-option-description="galaxySelectionDefaultDescription"
            @onSubmit="handleSubmit" />
    </BModal>
</template>

<style>
@import "user-styles.scss";

.modal-select-preferred-object-store {
    width: inherit;
    max-width: 800px;
}
</style>
