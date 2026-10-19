<script setup lang="ts">
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onUnmounted, watch } from "vue";

import { useConfig } from "@/composables/config";
import { useExportForAnotherGalaxy } from "@/composables/exportForAnotherGalaxy";
import { useExportToAnotherGalaxyStore } from "@/stores/exportToAnotherGalaxyStore";
import { copy as sendToClipboard } from "@/utils/clipboard";
import { formatDurationSeconds } from "@/utils/duration";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const store = useExportToAnotherGalaxyStore();
const { item } = storeToRefs(store);

const { config } = useConfig();
const { start, stateOf, stopAll } = useExportForAnotherGalaxy();

const showDialog = computed({
    get: () => Boolean(item.value),
    set: (show: boolean) => {
        if (!show) {
            store.close();
        }
    },
});
const noun = computed(() => (item.value?.contentType === "dataset_collection" ? "collection" : "dataset"));
const linkLifetime = computed(
    () => formatDurationSeconds(config.value?.short_term_storage_effective_duration) ?? "24 hours",
);
const shown = computed(() => (item.value ? stateOf(item.value) : undefined));
const link = computed(() => (shown.value?.status === "ready" ? shown.value.link : undefined));
const errorMessage = computed(() => (shown.value?.status === "failed" ? shown.value.error : undefined));

watch(item, (exportable) => {
    if (exportable) {
        start(exportable);
    }
});

onUnmounted(stopAll);
</script>

<template>
    <GModal v-model:show="showDialog" title="Export to another Galaxy" size="small">
        <GAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</GAlert>
        <div v-else-if="link">
            <BInputGroup>
                <BFormInput
                    :value="link"
                    readonly
                    aria-label="Link for another Galaxy"
                    data-description="galaxy export link" />
                <BInputGroupAppend>
                    <GButton color="blue" @click="sendToClipboard(link, 'Link copied to your clipboard')">
                        <FontAwesomeIcon :icon="faCopy" />
                        Copy
                    </GButton>
                </BInputGroupAppend>
            </BInputGroup>
            <p class="mt-2">
                Anyone with this link can download this {{ noun }} without logging in, until the link expires (usually
                after {{ linkLifetime }}). It can't be withdrawn before then.
            </p>
            <p>
                On the other Galaxy, open Upload and choose <b>Import from Another Galaxy</b>. Your exports are also
                listed under <router-link to="/downloads" @click="showDialog = false">Recent Exports</router-link>.
            </p>
        </div>
        <LoadingSpan v-else message="Preparing the export" />
    </GModal>
</template>
