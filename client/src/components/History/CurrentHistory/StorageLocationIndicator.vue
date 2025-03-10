<script setup lang="ts">
import { faHdd } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { HistorySummary } from "@/api";
import { useSync } from "@/composables/sync";
import { useObjectStoreStore } from "@/stores/objectStoreStore";
import { useUserStore } from "@/stores/userStore";

import SelectPreferredStore from "./SelectPreferredStore.vue";

const props = defineProps<{
    history: HistorySummary;
}>();

const preferredObjectStoreId = ref<string | null>(null);
useSync(() => props.history.preferred_object_store_id, preferredObjectStoreId);

const objectStoreStore = useObjectStoreStore();
objectStoreStore.fetchObjectStores();

const { currentUser, isAnonymous } = storeToRefs(useUserStore());

const userPreferredObjectStoreId = computed(() => {
    const user = currentUser.value;

    if (user && "preferred_object_store_id" in user) {
        return user.preferred_object_store_id ?? null;
    } else {
        return null;
    }
});

function onUpdatePreferredObjectStoreId(id: string | null) {
    preferredObjectStoreId.value = id;
}

const selectPreferredStore = ref<InstanceType<typeof SelectPreferredStore>>();

const storageLocationButtonTitle = computed(() => {
    if (!isAnonymous.value) {
        return "View and select storage location";
    } else {
        return "Log in to view and select storage location";
    }
});
</script>

<template>
    <div class="storage-location-indicator">
        <BButton
            class="ui-link"
            :title="storageLocationButtonTitle"
            :disabled="isAnonymous"
            @click="selectPreferredStore?.showModal()">
            <FontAwesomeIcon :icon="faHdd" />
            {{ objectStoreStore.getObjectStoreNameById(preferredObjectStoreId) ?? "Default Storage" }}
        </BButton>

        <SelectPreferredStore
            ref="selectPreferredStore"
            show-sub-setting
            :user-preferred-object-store-id="userPreferredObjectStoreId"
            :preferred-object-store-id="preferredObjectStoreId"
            :history="history"
            @updated="onUpdatePreferredObjectStoreId" />
    </div>
</template>

<style lang="scss" scoped>
.storage-location-indicator {
    margin: 0.5rem 0;
}
</style>
