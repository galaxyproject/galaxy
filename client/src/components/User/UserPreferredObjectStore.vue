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
    <BRow class="ml-3 mb-1">
        <FontAwesomeIcon :icon="faHdd" class="pt-1 mr-auto" size="lg" />

        <div class="pref-content pr-1">
            <a
                id="select-preferred-object-store"
                v-b-modal.modal-select-preferred-object-store
                class="preferred-storage"
                href="javascript:void(0)">
                <b v-localize>{{ title }}</b>
            </a>

            <div v-localize class="form-text text-muted">
                Select a {{ preferredOrEmptyString }} Galaxy storage for the outputs of new jobs.
            </div>

            <BModal
                id="modal-select-preferred-object-store"
                ref="modal"
                scrollable
                centered
                :title="title"
                hide-footer
                static
                size="lg"
                title-tag="h2"
                dialog-class="modal-select-preferred-object-store"
                @hidden="resetModal">
                <SelectObjectStore
                    :parent-error="error"
                    :selected-object-store-id="selectedObjectStoreId"
                    for-what="New dataset outputs from tools and workflows"
                    default-option-title="Galaxy Defaults"
                    default-option-description="Selecting this will reset Galaxy to default behaviors configured by your Galaxy administrator."
                    @onSubmit="handleSubmit" />
            </BModal>
        </div>
    </BRow>
</template>

<style>
@import "user-styles.scss";

.modal-select-preferred-object-store {
    width: inherit;
    max-width: 800px;
}
</style>
