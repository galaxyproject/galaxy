<script setup lang="ts">
import axios from "axios";
import { BModal } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { isRegisteredUser } from "@/api";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";
import { prependPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import SelectObjectStore from "@/components/ObjectStore/SelectObjectStore.vue";

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const { isLoaded: isConfigLoaded, config } = storeToRefs(useConfigStore());

const error = ref();
const selectedObjectStoreId = ref(
    isRegisteredUser(currentUser.value) ? currentUser.value?.preferred_object_store_id ?? null : null
);

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
        scrollable
        centered
        :title="title"
        title-tag="h3"
        static
        visible
        size="lg"
        dialog-class="modal-select-preferred-object-store"
        ok-only
        ok-title="Close"
        @hidden="resetModal">
        <SelectObjectStore
            :parent-error="error"
            :selected-object-store-id="selectedObjectStoreId"
            for-what="New dataset outputs from tools and workflows"
            default-option-title="Galaxy Defaults"
            default-option-description="Selecting this will reset Galaxy to default behaviors configured by your Galaxy administrator."
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
