<script setup lang="ts">
import { faLock } from "@fortawesome/free-solid-svg-icons";
import { computed } from "vue";

import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import AsyncButton from "../Common/AsyncButton.vue";
import PortletSection from "../Common/PortletSection.vue";

const props = defineProps<{
    historyId: string;
}>();

const emit = defineEmits<{
    (e: "history-made-private", sharingStatusChanged: boolean): void;
}>();

const historyStore = useHistoryStore();

const history = computed(() => historyStore.getHistoryById(props.historyId, true));

async function makeHistoryPrivate() {
    try {
        if (!history.value) {
            throw new Error("History not found");
        }
        const { sharingStatusChanged, skippedDatasets } = await historyStore.secureHistory(history.value);
        Toast.success(
            localize(
                "Your data in this history is now private, as well as any new data created in this history. \
                Your sharing preferences have also been reset.",
            ),
            localize("Successfully made history private."),
        );
        if (skippedDatasets > 0) {
            Toast.warning(
                `${skippedDatasets} ${localize(
                    "dataset(s) in this history belong to another user and remain accessible to others.",
                )}`,
                localize("Some datasets were not made private."),
            );
        }
        emit("history-made-private", sharingStatusChanged);
    } catch (error) {
        Toast.error(errorMessageAsString(error), localize("An error occurred while making the history private."));
    }
}
</script>

<template>
    <PortletSection :icon="faLock">
        <template v-slot:title>
            {{ localize("Make history") }}
            "{{ historyStore.getHistoryNameById(props.historyId) }}"
            {{ localize("private?") }}
        </template>

        <p v-localize>
            This will make the datasets you own in this history private (excluding library datasets), and will set
            permissions such that all new data is created as private. Datasets that belong to another user, for example
            those in a history you imported, stay as they are. Any datasets within that are currently shared will need
            to be re-shared or published. Are you sure you want to do this?
        </p>

        <AsyncButton
            data-description="history make private"
            :icon="faLock"
            :disabled="!history"
            variant="primary"
            :action="makeHistoryPrivate">
            {{ localize("Make History Private") }}
        </AsyncButton>
    </PortletSection>
</template>
