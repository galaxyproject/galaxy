<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { isAdminUser, isAnonymousUser } from "@/api";
import type { TourRequirements, TourStep as TourStepType } from "@/api/tours";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GModal from "../BaseComponents/GModal.vue";
import LoadingSpan from "../LoadingSpan.vue";
import TourStep from "./TourStep.vue";

/** Popup display duration when auto-playing the tour */
const PLAY_DELAY = 3000;

/** A `TourStep` (from backend schema) but with additional before and next actions
 *
 * This is there for the legacy `runTour` mounting method (used in webhooks) which provides its own
 * `onBefore` and `onNext` hooks for each step.
 *
 * For when `TourRunner` is parent, we simply use the prop `onBefore` and `onNext` methods and the `TourStep` type.
 */
type TourStepWithActions = TourStepType & {
    onBefore?: () => Promise<void>;
    onNext?: () => Promise<void>;
};

const props = defineProps<{
    steps: (TourStepType | TourStepWithActions)[];
    requirements: TourRequirements;
    tourId?: string;
    onBefore?: (step: TourStepType) => Promise<void>;
    onNext?: (step: TourStepType) => Promise<void>;
}>();

const emit = defineEmits(["end-tour"]);

const router = useRouter();

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
    cancelText?: "End Tour";
    ok?: () => Promise<void>;
} | null>(() => {
    if (errorMessage.value) {
        return {
            title: "Tour Failed",
            message: errorMessage.value,
            variant: "danger",
            ok: async () => {
                errorMessage.value = "";
                isPlaying.value = false;
            },
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
                okText: router ? "Login or Register" : undefined,
                cancelText: "End Tour",
                ok: async () => {
                    endTour();
                    if (router) {
                        router.push(`/login/start${props.tourId ? `?redirect=/tours/${props.tourId}` : ""}`);
                    }
                },
            };
        }
        if (props.requirements.indexOf("admin") >= 0 && !isAdminUser(currentUser.value)) {
            return {
                title: "Requires Admin",
                message: "You must be an admin to use this tour.",
                variant: "info",
                okText: router ? "Exit Tour" : undefined,
                cancelText: "End Tour",
                ok: async () => {
                    endTour();
                    if (router) {
                        if (isAnonymousUser(currentUser.value)) {
                            router.push(`/login/start${props.tourId ? `?redirect=/tours/${props.tourId}` : ""}`);
                        } else {
                            router.push("/");
                        }
                    }
                },
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
                cancelText: "End Tour",
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
const modalRef = ref<InstanceType<typeof GModal> | null>(null);

// Wait for GModal to render and then force show
// (We needed this, without this the GModal wouldn't show via the .sync prop)
watch(
    () => modalContents.value,
    async (newValue) => {
        if (Boolean(newValue) !== showModal.value) {
            showModal.value = Boolean(newValue);

            if (showModal.value) {
                await nextTick();
                modalRef.value?.showModal?.();
            }
        }
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
        if (currentStep.value) {
            if ("onNext" in currentStep.value && currentStep.value.onNext) {
                await currentStep.value.onNext();
            } else {
                await props.onNext?.(currentStep.value);
            }
        }
        // do pre-actions
        const nextIndex = currentIndex.value + 1;
        if (nextIndex < numberOfSteps.value && currentIndex.value !== -1) {
            const nextStep = props.steps[nextIndex];
            if (nextStep) {
                if ("onBefore" in nextStep && nextStep.onBefore) {
                    await nextStep.onBefore();
                } else {
                    await props.onBefore?.(nextStep);
                }

                // automatically continues to next step if enabled, unless its the last one
                if (isPlaying.value && nextIndex !== numberOfSteps.value - 1) {
                    setTimeout(() => {
                        if (isPlaying.value) {
                            next();
                        }
                    }, PLAY_DELAY);
                }
            }
        } else {
            // End Tour
            endTour();
        }
        // go to next step
        currentIndex.value = nextIndex;
    } catch (e) {
        errorMessage.value = errorMessageAsString(e);
    }
}

/** Ends the tour
 *
 * _In the case that_ `TourRunner` _is the parent, this will unmount the component._
 */
function endTour() {
    currentIndex.value = -1;
    isPlaying.value = false;
    errorMessage.value = "";

    // IMPORTANT: This is what unmounts the `TourRunner` component when that is the parent
    emit("end-tour");
}

async function handleKeyup(e: KeyboardEvent) {
    switch (e.keyCode) {
        case 39:
            await next();
            break;
        case 27:
            endTour();
            break;
    }
}

function modalDismiss(ok = true) {
    if (modalContents.value?.ok && (ok || errorMessage.value)) {
        modalContents.value.ok();
    } else if (modalContents.value?.cancelText === "End Tour") {
        endTour();
    }
}
</script>

<template>
    <div class="d-flex flex-column">
        <GModal
            v-if="modalContents !== null"
            id="tour-requirement"
            ref="modalRef"
            show
            :confirm="!errorMessage && modalContents.ok !== undefined"
            :ok-text="modalContents.okText"
            :cancel-text="modalContents.cancelText"
            :title="modalContents.title"
            size="small"
            :footer="Boolean(errorMessage)"
            @ok="modalDismiss"
            @cancel="modalDismiss(false)">
            <BAlert :variant="modalContents.variant" show>
                <span v-if="!modalContents.loading">{{ modalContents.message }}</span>
                <LoadingSpan v-else :message="modalContents.message" />
            </BAlert>
            <div v-if="errorMessage">
                The tour encountered an issue and cannot continue to the next step. This may be due to:
                <ul class="mb-2">
                    <li>Required interface elements not being visible or accessible</li>
                    <li>Page content still loading</li>
                    <li>Browser or network connectivity issues</li>
                </ul>
            </div>
            <template v-slot:footer>
                <span v-if="errorMessage">Exit to retry the current step.</span>
                <span v-else-if="modalContents.cancelText === 'End Tour'">Closing this modal ends the tour.</span>
            </template>
        </GModal>
        <TourStep
            v-if="modalContents === null && currentHistory && currentStep && currentUser"
            :key="currentIndex"
            :step="currentStep"
            :is-playing="isPlaying"
            :is-last="isLast"
            @next="next"
            @end="endTour"
            @play="play" />
    </div>
</template>
