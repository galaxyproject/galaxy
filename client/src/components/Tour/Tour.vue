<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onUnmounted, ref, watch } from "vue";

import { isAdminUser, isAnonymousUser } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GModal from "../BaseComponents/GModal.vue";
import LoadingSpan from "../LoadingSpan.vue";
import TourStep from "./TourStep.vue";

/** Popup display duration when auto-playing the tour */
const PLAY_DELAY = 3000;

const props = defineProps<{
    steps: { title: string; content: string; onNext?: () => Promise<void>; onBefore?: () => Promise<void> }[];
    requirements: string[];
}>();

const currentIndex = ref(-1);
const errorMessage = ref("");
const isPlaying = ref(false);

// Store variables
const historyStore = useHistoryStore();
const { currentHistory, historiesLoading } = storeToRefs(historyStore);
const { currentUser } = storeToRefs(useUserStore());

// Step variables
const currentStep = computed(() => props.steps[currentIndex.value]);
const numberOfSteps = computed(() => props.steps.length);
const isFirst = computed(() => currentIndex.value === 0);
const isLast = computed(() => currentIndex.value === props.steps.length - 1);

/** On some conditions here, a message modal is shown and the tour doesn't start
 * when these conditions are met. This returns the contents of the modal if it should be shown.
 */
const modalContents = computed<{
    title: string;
    message: string;
    variant: "danger" | "info";
    loading?: boolean;
    okText?: string;
    ok?: () => Promise<void>;
} | null>(() => {
    if (errorMessage.value) {
        return {
            title: "Tour Failed",
            message: errorMessage.value,
            variant: "danger",
        };
    }

    if (historiesLoading.value) {
        return {
            title: "Preparing Tour",
            message: "Evaluating Requirements",
            variant: "info",
            loading: true,
        };
    }

    if (isFirst.value) {
        if (props.requirements.indexOf("logged_in") >= 0 && isAnonymousUser(currentUser.value)) {
            return {
                title: "Requires Login",
                message: "You must log in to Galaxy to use this tour.",
                variant: "info",
            };
        }
        if (props.requirements.indexOf("admin") >= 0 && !isAdminUser(currentUser.value)) {
            return {
                title: "Requires Admin",
                message: "You must be an admin to use this tour.",
                variant: "info",
            };
        }
        // TODO: better estimate for whether the history is new.
        if (props.requirements.indexOf("new_history") >= 0 && currentHistory.value && currentHistory.value.size !== 0) {
            return {
                title: "Requires New History",
                message:
                    "This tour is designed to run on a new history, please create a new history before running it.",
                variant: "info",
                okText: "Create New History",
                ok: async () => {
                    await historyStore.createNewHistory();
                },
            };
        }
    }
    return null;
});

// We use this ref to control the modal visibility
const showModal = ref(false);
watch(
    () => modalContents.value,
    (newValue) => {
        showModal.value = newValue !== null;
    },
    { immediate: true },
);

start();

onUnmounted(() => {
    window.removeEventListener("keyup", handleKeyup);
});

function start() {
    window.addEventListener("keyup", handleKeyup);
    currentIndex.value = 0;
}

function play(isCurrentlyPlaying: boolean) {
    isPlaying.value = isCurrentlyPlaying;
    if (isPlaying.value) {
        next();
    }
}

async function next() {
    try {
        // do post-actions
        if (currentStep.value && currentStep.value.onNext) {
            await currentStep.value.onNext();
        }
        // do pre-actions
        const nextIndex = currentIndex.value + 1;
        if (nextIndex < numberOfSteps.value && currentIndex.value !== -1) {
            const nextStep = props.steps[nextIndex];
            if (nextStep?.onBefore) {
                await nextStep.onBefore();
                // automatically continues to next step if enabled, unless its the last one
                if (isPlaying.value && nextIndex !== numberOfSteps.value - 1) {
                    setTimeout(() => {
                        if (isPlaying.value) {
                            next();
                        }
                    }, PLAY_DELAY);
                }
            }
        }
        // go to next step
        currentIndex.value = nextIndex;
    } catch (e) {
        errorMessage.value = errorMessageAsString(e);
    }
}

function end() {
    currentIndex.value = -1;
    isPlaying.value = false;
}

async function handleKeyup(e: KeyboardEvent) {
    switch (e.keyCode) {
        case 39:
            await next();
            break;
        case 27:
            end();
            break;
    }
}
</script>

<template>
    <div class="d-flex flex-column">
        <GModal
            id="tour-requirement"
            :show.sync="showModal"
            :confirm="modalContents?.ok !== undefined"
            :ok-text="modalContents?.okText"
            :title="modalContents?.title"
            size="small"
            @ok="modalContents?.ok">
            <BAlert :variant="modalContents?.variant" show>
                <span v-if="!modalContents?.loading">{{ modalContents?.message }}</span>
                <LoadingSpan v-else :message="modalContents?.message" />
            </BAlert>
        </GModal>
        <TourStep
            v-if="modalContents === null && currentHistory && currentStep && currentUser"
            :key="currentIndex"
            :step="currentStep"
            :is-playing="isPlaying"
            :is-last="isLast"
            @next="next"
            @end="end"
            @play="play" />
    </div>
</template>
