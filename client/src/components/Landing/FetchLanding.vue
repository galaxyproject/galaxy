<script setup lang="ts">
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";
import { ref } from "vue";

import type { FetchTargets } from "@/api/tools";
import { useFetchJobMonitor } from "@/composables/fetch";
import { useHistoryStore } from "@/stores/historyStore";

import FetchGrids from "./FetchGrids.vue";
import ButtonSpinner from "@/components/Common/ButtonSpinner.vue";
import FormCardSticky from "@/components/Form/FormCardSticky.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const { currentHistoryId } = storeToRefs(useHistoryStore());

interface Props {
    targets: FetchTargets;
    landingUuid?: string;
}

const props = defineProps<Props>();
const fetchGrids = ref();
const errorText = ref<string | null>(null);
const description = "(review data to be imported)";
const title = "Import Data";
const runTitle = "Import";
const runTooltip = "Begin data import";

interface FetchGridComponent {
    asTargets(): FetchTargets;
}

async function onExecute() {
    const historyId = currentHistoryId.value;
    if (!historyId) {
        console.log("Logic error - no current history ID set, cannot execute fetch job.");
        return;
    }
    const component = fetchGrids.value as FetchGridComponent;
    const request = component.asTargets();
    fetchAndWatch({
        targets: request,
        history_id: historyId,
        landing_uuid: props.landingUuid,
    });
}

const { fetchAndWatch, fetchComplete, fetchError, waitingOnFetch } = useFetchJobMonitor();
</script>

<template>
    <FormCardSticky
        :error-message="errorText || ''"
        :description="description"
        :name="title"
        :icon="faUpload"
        :version="undefined">
        <template v-slot:buttons>
            <b-button-group class="tool-card-buttons">
                <ButtonSpinner
                    id="execute"
                    class="text-nowrap"
                    :title="runTitle"
                    :disabled="!currentHistoryId"
                    size="small"
                    :wait="waitingOnFetch"
                    :tooltip="runTooltip"
                    @onClick="onExecute" />
            </b-button-group>
        </template>
        <template v-slot>
            <LoadingSpan v-if="!currentHistoryId" />
            <BAlert v-else-if="fetchComplete" variant="success" show> Data imported successfully. </BAlert>
            <BAlert v-else-if="fetchError" variant="danger" show> Error importing data: {{ fetchError }} </BAlert>
            <BAlert v-else-if="waitingOnFetch" variant="info" show>
                <LoadingSpan message="Importing data" />
            </BAlert>
            <FetchGrids v-else ref="fetchGrids" :targets="props.targets" />
        </template>
    </FormCardSticky>
</template>

<style lang="scss" scoped>
.tool-card-buttons {
    height: 2em;
}
</style>
