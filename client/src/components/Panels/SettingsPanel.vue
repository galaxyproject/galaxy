<script setup lang="ts">
import { faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import { useConfirmDialog } from "@/composables/confirmDialog";
import { useActivityStore } from "@/stores/activityStore";
import localize from "@/utils/localization";

import GButton from "../BaseComponents/GButton.vue";
import ActivitySettings from "@/components/ActivityBar/ActivitySettings.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const props = defineProps<{
    activityBarId: string;
    heading: string;
    searchPlaceholder: string;
}>();

const emit = defineEmits<{
    (e: "activityClicked", activityId: string): void;
}>();

const { confirm } = useConfirmDialog();

const activityStore = useActivityStore(props.activityBarId);

const query = ref("");

async function confirmRestore() {
    const confirmed = await confirm(
        localize("Are you sure you want to reset the activity bar to its default settings?"),
        {
            title: localize("Restore Activity Bar Defaults"),
        },
    );

    if (confirmed) {
        activityStore.restore();
    }
}

function onQuery(newQuery: string) {
    query.value = newQuery;
}
</script>

<template>
    <ActivityPanel :title="props.heading">
        <template v-slot:header>
            <DelayedInput :delay="100" :placeholder="props.searchPlaceholder" @change="onQuery" />
        </template>
        <template v-slot:header-buttons>
            <GButton
                data-description="restore factory settings"
                size="small"
                transparent
                color="blue"
                :title="localize('Restore default')"
                @click="confirmRestore">
                <span v-localize>Reset</span>
                <FontAwesomeIcon :icon="faUndo" fixed-width />
            </GButton>
        </template>
        <ActivitySettings
            :query="query"
            :activity-bar-id="props.activityBarId"
            @activityClicked="(...args) => emit('activityClicked', ...args)" />
    </ActivityPanel>
</template>
