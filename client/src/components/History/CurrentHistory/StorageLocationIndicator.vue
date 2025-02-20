<script setup lang="ts">
import { faHdd } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BModal } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { HistorySummary } from "@/api";
import { useStorageLocationConfiguration } from "@/composables/storageLocation";
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

const modalShown = ref(false);
const { currentUser } = storeToRefs(useUserStore());

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

const { isOnlyPreference } = useStorageLocationConfiguration();
const storageLocationTitle = computed(() => {
    if (isOnlyPreference.value) {
        return "History Preferred Storage Location";
    } else {
        return "History Storage Location";
    }
});
</script>

<template>
    <div class="storage-location-indicator">
        <BButton class="ui-link" @click="modalShown = true">
            <FontAwesomeIcon :icon="faHdd" />
            {{ objectStoreStore.getObjectStoreNameById(preferredObjectStoreId) ?? "Default Storage" }}
        </BButton>

        <BModal v-model="modalShown" :title="storageLocationTitle" ok-only title-tag="h2" title-class="h-sm">
            <SelectPreferredStore
                :user-preferred-object-store-id="userPreferredObjectStoreId"
                :preferred-object-store-id="preferredObjectStoreId"
                :history="history"
                @updated="onUpdatePreferredObjectStoreId" />
        </BModal>
    </div>
</template>

<style lang="scss" scoped>
.storage-location-indicator {
    margin: 0.5rem 0;
}
</style>
