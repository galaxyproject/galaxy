<script setup lang="ts">
import { faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BModal } from "bootstrap-vue";
import { ref } from "vue";

import { useActivityStore } from "@/stores/activityStore";

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

const activityStore = useActivityStore(props.activityBarId);

const confirmRestore = ref(false);
const query = ref("");

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
            <BButton
                v-b-tooltip.bottom.hover
                data-description="恢复出厂设置"
                size="sm"
                variant="link"
                title="恢复默认"
                @click="confirmRestore = true">
                <span v-localize>重置</span>
                <FontAwesomeIcon :icon="faUndo" fixed-width />
            </BButton>
        </template>
        <ActivitySettings
            :query="query"
            :activity-bar-id="props.activityBarId"
            @activityClicked="(...args) => emit('activityClicked', ...args)" />
        <BModal
            v-model="confirmRestore"
            title="恢复活动栏默认设置"
            title-tag="h2"
            @ok="activityStore.restore()">
            <p v-localize>您确定要将活动栏重置为默认设置吗？</p>
        </BModal>
    </ActivityPanel>
</template>
