<script setup lang="ts">
import { faLock } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import AsyncButton from "../Common/AsyncButton.vue";

const props = defineProps<{
    historyId: string;
}>();

const emit = defineEmits(["change"]);

const historyStore = useHistoryStore();

const history = computed(() => historyStore.getHistoryById(props.historyId, true));

async function makeHistoryPrivate() {
    try {
        if (!history.value) {
            throw new Error("History not found");
        }
        await historyStore.secureHistory(history.value);
        Toast.success(
            localize(
                "Existing data in this history is now private, as well as any new data created in this history. \
                Your sharing preferences have also been reset."
            ),
            localize("Successfully made history private.")
        );
        emit("change");
    } catch (error) {
        Toast.error(errorMessageAsString(error), localize("An error occurred while making the history private."));
    }
}
</script>

<template>
    <div v-if="history" class="ui-portlet-section">
        <div class="portlet-header">
            <span class="portlet-title">
                <FontAwesomeIcon :icon="faLock" class="portlet-title-icon mr-1" />

                <b class="portlet-title-text">
                    {{ localize("Make history") }}
                    "{{ history.name }}"
                    {{ localize("private?") }}
                </b>
            </span>
        </div>

        <div class="portlet-content">
            <div class="mt-3">
                <p v-localize>
                    This will make all the data in this history private (excluding library datasets), and will set
                    permissions such that all new data is created as private. Any datasets within that are currently
                    shared will need to be re-shared or published. Are you sure you want to do this?
                </p>

                <AsyncButton :icon="faLock" variant="primary" :action="makeHistoryPrivate">
                    {{ localize("Make History Private") }}
                </AsyncButton>
            </div>
        </div>
    </div>
</template>
