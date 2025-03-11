<script setup lang="ts">
import { faLock, faShareAlt, faUserLock } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BTab, BTabs } from "bootstrap-vue";
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

const tabsLazy = ref(false);
</script>

<template>
    <div aria-labelledby="history-sharing-heading">
        <Heading id="history-sharing-heading" h1 separator inline truncate size="xl">
            {{ localize("Manage History") }}
            "{{ historyStore.getHistoryNameById(props.historyId) }}"
        </Heading>

        <BTabs class="mt-3">
            <BTab :lazy="tabsLazy" @click="tabsLazy = false">
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faShareAlt" class="mr-1" />
                    {{ localize("Share or Publish") }}
                </template>

                <SharingPage :id="props.historyId" plural-name="histories" model-class="History" no-heading />
            </BTab>

            <BTab :lazy="tabsLazy" @click="tabsLazy = false">
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

                <HistoryMakePrivate :history-id="props.historyId" @change="tabsLazy = true" />
            </BTab>
        </BTabs>
    </div>
</template>
