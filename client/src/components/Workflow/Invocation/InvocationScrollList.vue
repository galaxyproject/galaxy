<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye } from "@fortawesome/free-regular-svg-icons";
import { faArrowDown, faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useInfiniteScroll } from "@vueuse/core";
import { BAlert, BBadge, BButton, BListGroup, BListGroupItem } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import type { WorkflowInvocation } from "@/api/invocations";
import { getData } from "@/components/Grid/configs/invocations";
import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ScrollToTopButton from "@/components/ToolsList/ScrollToTopButton.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    inPanel?: boolean;
    limit?: number;
}

const props = withDefaults(defineProps<Props>(), {
    inPanel: false,
    limit: 20,
});

const emit = defineEmits(["invocation-clicked"]);

library.add(faEye, faArrowDown, faInfoCircle);

const stateClasses: Record<string, string> = {
    ready: "waiting",
    scheduled: "ok",
    failed: "error",
};

const busy = ref(false);
const errorMessage = ref("");
const initDataLoading = ref(true);
const invocations = ref<WorkflowInvocation[]>([]);
const totalInvocationCount = ref<number | undefined>(undefined);
const currentPage = ref(0);
const scrollableDiv = ref<HTMLElement | null>(null);

const { currentUser } = storeToRefs(useUserStore());

const allLoaded = computed(
    () => totalInvocationCount.value !== undefined && totalInvocationCount.value <= invocations.value.length
);

// check if we have scrolled to the top or bottom of the scrollable div
const { arrived, scrollTop } = useAnimationFrameScroll(scrollableDiv);
const isScrollable = ref(false);
useAnimationFrameResizeObserver(scrollableDiv, ({ clientSize, scrollSize }) => {
    isScrollable.value = scrollSize.height >= clientSize.height + 1;
});
const scrolledTop = computed(() => !isScrollable.value || arrived.top);
const scrolledBottom = computed(() => !isScrollable.value || arrived.bottom);

onMounted(async () => {
    useInfiniteScroll(scrollableDiv.value, () => loadInvocations());
});

onUnmounted(() => {
    // Remove the infinite scrolling behavior
    useInfiniteScroll(scrollableDiv.value, () => {});
});

/** if screen size is as such that a scroller is not rendered,
 * we load enough invocations so that a scroller is rendered
 */
watch(
    () => isScrollable.value,
    (scrollable: boolean) => {
        if (!scrollable && !allLoaded.value) {
            loadInvocations();
        }
    }
);

const currentItemId = computed(() => {
    const path = route.path;
    const match = path.match(/\/workflows\/invocations\/([a-zA-Z0-9]+)/);
    return match ? match[1] : undefined;
});

const route = useRoute();
const router = useRouter();

function cardClicked(invocation: WorkflowInvocation) {
    let path = `/workflows/invocations/${invocation.id}`;
    if (props.inPanel) {
        path += "?from_panel=true";
        emit("invocation-clicked");
    }
    router.push(path);
}

function scrollToTop() {
    scrollableDiv.value?.scrollTo({ top: 0, behavior: "smooth" });
}

/**
 * Request invocations for the current user
 */
async function loadInvocations() {
    if (currentUser.value && !currentUser.value.isAnonymous && !busy.value && !allLoaded.value) {
        busy.value = true;
        try {
            const offset = props.limit * currentPage.value;
            const extraProps = currentUser.value ? { user_id: currentUser.value.id } : {};

            const [responseData, responseTotal] = await getData(
                offset,
                props.limit,
                "",
                "create_time",
                true,
                extraProps
            );
            invocations.value = invocations.value.concat(responseData as WorkflowInvocation[]);
            totalInvocationCount.value = responseTotal as number;
            currentPage.value += 1;
            errorMessage.value = "";
        } catch (e) {
            errorMessage.value = `Failed to obtain invocations: ${e}`;
        } finally {
            initDataLoading.value = false;
            busy.value = false;
        }
    }
}

function historyName(historyId: string) {
    const historyStore = useHistoryStore();
    return historyStore.getHistoryNameById(historyId);
}

function stateClass(state: WorkflowInvocation["state"]) {
    if (stateClasses[state]) {
        return `node-header-invocation header-${stateClasses[state]}`;
    }
    return "";
}

function workflowName(workflowId: string) {
    const workflowStore = useWorkflowStore();
    return workflowStore.getStoredWorkflowNameByInstanceId(workflowId);
}
</script>

<template>
    <div :class="props.inPanel ? 'unified-panel' : 'flex-column-overflow'">
        <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <BAlert v-else-if="initDataLoading" variant="info" show>
            <LoadingSpan message="Loading invocations" />
        </BAlert>
        <BAlert v-else-if="totalInvocationCount === 0" show>
            <h4>
                <FontAwesomeIcon :icon="faInfoCircle" />
                <span v-localize>No invocations yet.</span>
            </h4>

            <p>
                <span v-localize>Run </span>
                <router-link to="/workflows/list">workflows</router-link>
                <span v-localize> to see invocations here.</span>
            </p>
        </BAlert>
        <div
            class="scroll-list-container"
            :class="{
                'in-panel': props.inPanel,
                'scrolled-top': scrolledTop,
                'scrolled-bottom': scrolledBottom,
            }">
            <div
                ref="scrollableDiv"
                class="scroll-list"
                :class="{
                    'in-panel': props.inPanel,
                    toolMenuContainer: props.inPanel,
                }"
                role="list">
                <BListGroup>
                    <BListGroupItem
                        v-for="(invocation, cardIndex) in invocations"
                        :key="cardIndex"
                        button
                        class="d-flex"
                        :class="{
                            current: invocation.id === currentItemId,
                            'panel-item': props.inPanel,
                        }"
                        :active="invocation.id === currentItemId"
                        @click="() => cardClicked(invocation)">
                        <div class="overflow-auto w-100">
                            <Heading bold size="text" icon="fa-sitemap">
                                <span class="truncate-n-lines three-lines">
                                    {{ workflowName(invocation.workflow_id) }}
                                </span>
                            </Heading>
                            <Heading size="text" icon="fa-hdd">
                                <small class="text-muted truncate-n-lines two-lines">
                                    {{ historyName(invocation.history_id) }}
                                </small>
                            </Heading>
                            <div class="d-flex justify-content-between">
                                <BBadge v-b-tooltip.noninteractive.hover pill>
                                    <UtcDate :date="invocation.create_time" mode="elapsed" />
                                </BBadge>
                                <BBadge v-b-tooltip.noninteractive.hover pill :class="stateClass(invocation.state)">
                                    {{ invocation.state }}
                                </BBadge>
                            </div>
                        </div>
                        <div v-if="props.inPanel" class="position-absolute mr-3" style="right: 0">
                            <FontAwesomeIcon v-if="invocation.id === currentItemId" :icon="faEye" size="lg" />
                        </div>
                    </BListGroupItem>
                    <div>
                        <div v-if="allLoaded" class="list-end my-2">
                            <span v-if="invocations.length == 1">- {{ invocations.length }} invocation loaded -</span>
                            <span v-else-if="invocations.length > 1">
                                - All {{ invocations.length }} invocations loaded -
                            </span>
                        </div>
                        <BOverlay :show="busy" opacity="0.5" />
                    </div>
                </BListGroup>
            </div>
            <ScrollToTopButton :offset="scrollTop" @click="scrollToTop" />
        </div>

        <div :class="!props.inPanel && 'd-flex flex-row mt-3'">
            <div
                v-if="!allLoaded"
                class="mr-auto d-flex justify-content-center align-items-center"
                :class="props.inPanel && 'mt-1'">
                <i class="mr-1">Loaded {{ invocations.length }} out of {{ totalInvocationCount }} invocations</i>
                <BButton
                    v-b-tooltip.noninteractive.hover
                    data-description="load more invocations button"
                    size="sm"
                    title="Load More"
                    variant="link"
                    @click="loadInvocations()">
                    <FontAwesomeIcon :icon="faArrowDown" />
                </BButton>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
.truncate-n-lines {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-word;
    overflow-wrap: break-word;
    &.three-lines {
        -webkit-line-clamp: 3;
        line-clamp: 3;
    }
    &.two-lines {
        -webkit-line-clamp: 2;
        line-clamp: 2;
    }
}
</style>
