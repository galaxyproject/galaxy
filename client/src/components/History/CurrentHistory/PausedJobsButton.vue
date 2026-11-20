<script setup lang="ts">
import { faPause } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import {
    type AnyUser,
    canMutateHistory,
    type HistorySummary,
    type HistorySummaryExtended,
    isUserOverQuota,
    userOwnsHistory,
} from "@/api";
import { resumePausedJobs } from "@/api/histories";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

const props = defineProps<{
    history: HistorySummary & Pick<HistorySummaryExtended, "paused_jobs_count">;
    currentUser: AnyUser;
}>();

const emit = defineEmits<{
    (e: "show-paused"): void;
}>();

const toast = useToast();
const historyStore = useHistoryStore();
const { otherSourcesOverQuota } = storeToRefs(useQuotaUsageStore());

const button = ref<InstanceType<typeof GButton> | null>(null);
const buttonElement = () => button.value?.$el;
const isPopoverShown = ref(false);
const resuming = ref(false);

const canResume = computed(() => userOwnsHistory(props.currentUser, props.history) && canMutateHistory(props.history));
// The history's own updates bring the count
const pausedCount = computed(() => (canResume.value ? (props.history.paused_jobs_count ?? 0) : 0));
// Jobs paused for the quota would only pause again
const isUserOverAnyQuota = computed(() => isUserOverQuota(props.currentUser) || otherSourcesOverQuota.value.length > 0);
// The number follows a colon, so the sentence translates whole
const pausedLabel = computed(() => `${localize("Jobs paused in this history:")} ${pausedCount.value}`);

function closePopover() {
    isPopoverShown.value = false;
}

watch(() => props.history.id, closePopover);

function onShowPaused() {
    closePopover();
    emit("show-paused");
}

async function onResumePausedJobs() {
    const historyId = props.history.id;
    resuming.value = true;
    try {
        await resumePausedJobs(historyId);
    } catch (e) {
        toast.error(errorMessageAsString(e));
        return;
    } finally {
        resuming.value = false;
    }
    closePopover();
    toast.success(localize("Paused jobs resumed."));
    // Brings the new count, like the panel does after changing its items
    historyStore
        .updateContentStats(historyId)
        .catch((e) => console.error("Error updating the history after resuming its paused jobs:", e));
}
</script>

<template>
    <span v-if="pausedCount > 0">
        <GButton
            ref="button"
            v-g-tooltip.hover
            :title="localize('Paused jobs')"
            :aria-label="`${localize('Paused jobs')} (${pausedCount})`"
            transparent
            color="blue"
            size="small"
            class="rounded-0 text-decoration-none"
            data-description="paused jobs button">
            <FontAwesomeIcon :icon="faPause" />
            <span>{{ pausedCount }}</span>
        </GButton>
        <GPopover
            v-model:show="isPopoverShown"
            :target="buttonElement"
            triggers="click"
            placement="bottom"
            :title="localize('Paused jobs')"
            data-description="paused jobs popover">
            <p class="mb-2">{{ pausedLabel }}</p>
            <p v-if="isUserOverAnyQuota" class="small mb-2" data-description="paused jobs over quota">
                {{ localize("You are over your disk quota. Free some space to resume them.") }}
            </p>
            <div class="d-flex flex-gapx-1">
                <GButton
                    size="small"
                    color="blue"
                    :disabled="isUserOverAnyQuota || resuming"
                    data-description="resume paused jobs button"
                    @click="onResumePausedJobs">
                    {{ localize("Resume all") }}
                </GButton>
                <GButton size="small" outline color="blue" data-description="show paused jobs" @click="onShowPaused">
                    {{ localize("Show them") }}
                </GButton>
            </div>
        </GPopover>
    </span>
</template>
