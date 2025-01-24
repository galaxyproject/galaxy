<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faExchangeAlt, faEye, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BButton, BButtonGroup } from "bootstrap-vue";
import { computed } from "vue";

import { type ArchivedHistorySummary } from "@/api/histories.archived";
import localize from "@/utils/localization";

import ExportRecordDOILink from "@/components/Common/ExportRecordDOILink.vue";
import Heading from "@/components/Common/Heading.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    history: ArchivedHistorySummary;
}

const props = defineProps<Props>();

const canImportCopy = computed(() => props.history.export_record_data?.target_uri !== undefined);

const emit = defineEmits<{
    (e: "onView", history: ArchivedHistorySummary): void;
    (e: "onSwitch", history: ArchivedHistorySummary): void;
    (e: "onRestore", history: ArchivedHistorySummary): void;
    (e: "onImportCopy", history: ArchivedHistorySummary): void;
}>();

library.add(faExchangeAlt, faUndo, faCopy, faEye);

function onViewHistoryInCenterPanel() {
    emit("onView", props.history);
}

function onSetAsCurrentHistory() {
    emit("onSwitch", props.history);
}

async function onRestoreHistory() {
    emit("onRestore", props.history);
}

async function onImportCopy() {
    emit("onImportCopy", props.history);
}
</script>

<template>
    <div class="archived-history-card">
        <div class="d-flex justify-content-between align-items-center">
            <Heading h3 inline bold size="sm">
                {{ history.name }} <ExportRecordDOILink :export-record-uri="history.export_record_data?.target_uri" />
            </Heading>

            <div class="d-flex align-items-center flex-gapx-1 badges">
                <BBadge v-if="history.published" v-b-tooltip pill :title="localize('This history is public.')">
                    {{ localize("Published") }}
                </BBadge>
                <BBadge v-if="!history.purged" v-b-tooltip pill :title="localize('Amount of items in history')">
                    {{ history.count }} {{ localize("items") }}
                </BBadge>
                <BBadge
                    v-if="history.export_record_data"
                    v-b-tooltip
                    pill
                    :title="
                        localize(
                            'This history has an associated export record containing a snapshot of the history that can be used to import a copy of the history.'
                        )
                    ">
                    {{ localize("Snapshot available") }}
                </BBadge>
                <BBadge v-b-tooltip pill :title="localize('Last edited/archived')">
                    <UtcDate :date="history.update_time" mode="elapsed" />
                </BBadge>
            </div>
        </div>

        <div class="d-flex justify-content-start align-items-center mt-1">
            <BButtonGroup class="actions">
                <BButton
                    v-b-tooltip
                    :title="localize('View this history')"
                    variant="link"
                    class="p-0 px-1"
                    @click.stop="onViewHistoryInCenterPanel">
                    <FontAwesomeIcon :icon="faEye" size="lg" />
                    View
                </BButton>
                <BButton
                    v-b-tooltip
                    :title="localize('Set as current history')"
                    variant="link"
                    class="p-0 px-1"
                    @click.stop="onSetAsCurrentHistory">
                    <FontAwesomeIcon :icon="faExchangeAlt" size="lg" />
                    Switch
                </BButton>
                <BButton
                    v-b-tooltip
                    :title="localize('Unarchive this history and move it back to your active histories')"
                    variant="link"
                    class="p-0 px-1"
                    @click.stop="onRestoreHistory">
                    <FontAwesomeIcon :icon="faUndo" size="lg" />
                    Unarchive
                </BButton>

                <BButton
                    v-if="canImportCopy"
                    v-b-tooltip
                    :title="localize('Import a new copy of this history from the associated export record')"
                    variant="link"
                    class="p-0 px-1"
                    @click.stop="onImportCopy">
                    <FontAwesomeIcon :icon="faCopy" size="lg" />
                    Import Copy
                </BButton>
            </BButtonGroup>
        </div>

        <p v-if="history.annotation" class="my-1">{{ history.annotation }}</p>

        <StatelessTags class="my-1" :value="history.tags" :disabled="true" :max-visible-tags="10" />
    </div>
</template>

<style scoped>
.badges {
    font-size: 1rem;
}
</style>
