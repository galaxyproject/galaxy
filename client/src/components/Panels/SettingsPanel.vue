<script setup lang="ts">
import { faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BModal } from "bootstrap-vue";
import { ref } from "vue";

import { useActivityStore } from "@/stores/activityStore";

import ActivitySettings from "@/components/ActivityBar/ActivitySettings.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const activityStore = useActivityStore();

const confirmRestore = ref(false);
const query = ref("");

function onQuery(newQuery: string) {
    query.value = newQuery;
}
</script>

<template>
    <ActivityPanel title="Additional Activities">
        <template v-slot:header>
            <DelayedInput :delay="100" placeholder="Search activities" @change="onQuery" />
        </template>
        <template v-slot:header-buttons>
            <BButton
                v-b-tooltip.bottom.hover
                data-description="restore factory settings"
                size="sm"
                variant="link"
                title="Restore default"
                @click="confirmRestore = true">
                <span v-localize>Reset</span>
                <FontAwesomeIcon :icon="faUndo" fixed-width />
            </BButton>
        </template>
        <ActivitySettings :query="query" />
        <BModal
            v-model="confirmRestore"
            title="Restore Activity Bar Defaults"
            title-tag="h2"
            @ok="activityStore.restore()">
            <p v-localize>Are you sure you want to reset the activity bar to its default settings?</p>
        </BModal>
    </ActivityPanel>
</template>
