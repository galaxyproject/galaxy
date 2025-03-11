<script setup lang="ts">
import { faExclamation, faLock, faShareAlt, faUserLock } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BTab, BTabs } from "bootstrap-vue";
import { ref } from "vue";

import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import Heading from "../Common/Heading.vue";
import SharingPage from "../Sharing/SharingPage.vue";
import HistoryDatasetPermissions from "./HistoryDatasetPermissions.vue";
import HistoryMakePrivate from "./HistoryMakePrivate.vue";

const props = defineProps<{
    historyId: string;
}>();

const historyStore = useHistoryStore();

/** This boolean is used to trigger lazy loading (refresh) of other tabs when history privacy has changed. */
const historyPrivacyChanged = ref(false);

/** Once the history is made private, this boolean is used to notify the user if sharing status has also changed or not. */
const sharingStatusChanged = ref(false);

function historyMadePrivate(hasSharingStatusChanged: boolean) {
    sharingStatusChanged.value = hasSharingStatusChanged;
    historyPrivacyChanged.value = true;
}

function openSharingTab() {
    historyPrivacyChanged.value = false;
    sharingStatusChanged.value = false;
}
</script>

<template>
    <div aria-labelledby="history-sharing-heading">
        <Heading id="history-sharing-heading" h1 separator inline truncate size="xl">
            {{ localize("Manage History") }}
            "{{ historyStore.getHistoryNameById(props.historyId) }}"
        </Heading>

        <BTabs class="mt-3">
            <BTab :lazy="historyPrivacyChanged" @click="openSharingTab">
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faShareAlt" class="mr-1" />
                    {{ localize("Share or Publish") }}
                    <BBadge
                        v-if="sharingStatusChanged"
                        v-b-tooltip.hover.noninteractive
                        class="ml-1"
                        :title="localize('Sharing status for this history has changed.')"
                        variant="primary">
                        <FontAwesomeIcon :icon="faExclamation" />
                    </BBadge>
                </template>

                <SharingPage :id="props.historyId" plural-name="histories" model-class="History" no-heading />
            </BTab>

            <BTab :lazy="historyPrivacyChanged" @click="historyPrivacyChanged = false">
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faUserLock" class="mr-1" />
                    {{ localize("Set Permissions") }}
                </template>

                <HistoryDatasetPermissions :history-id="props.historyId" no-redirect />
            </BTab>

            <BTab>
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faLock" class="mr-1" />
                    {{ localize("Make Private") }}
                </template>

                <HistoryMakePrivate :history-id="props.historyId" @history-made-private="historyMadePrivate" />
            </BTab>
        </BTabs>
    </div>
</template>
