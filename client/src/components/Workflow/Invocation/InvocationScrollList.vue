<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye } from "@fortawesome/free-regular-svg-icons";
import { faArrowDown, faInfoCircle, faHdd, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import type { WorkflowInvocation } from "@/api/invocations";
import { getData } from "@/components/Grid/configs/invocations";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import Heading from "@/components/Common/Heading.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";
import UtcDate from "@/components/UtcDate.vue";

const currentUser = computed(() => useUserStore().currentUser);

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

async function loadInvocations(offset: number, limit: number) {
    if (!currentUser.value || currentUser.value.isAnonymous) {
        return { items: [], total: 0 };
    }
    const extraProps = { user_id: currentUser.value.id };
    const [responseData, responseTotal] = await getData(offset, limit, "", "create_time", true, extraProps);
    return { items: responseData, total: responseTotal };
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

const route = useRoute();
const router = useRouter();

const currentItemId = computed(() => {
    const path = route.path;
    const match = path.match(/\/workflows\/invocations\/([a-zA-Z0-9]+)/);
    return match ? match[1] : undefined;
});

function cardClicked(invocation: WorkflowInvocation) {
    if (props.inPanel) {
        emit("invocation-clicked");
    }
    router.push(`/workflows/invocations/${invocation.id}`);
}
</script>

<template>
    <ScrollList :loader="loadInvocations" :item-key="(invocation) => invocation.id" :in-panel="inPanel">
        <template v-slot:item="{ item: invocation }">
            <BListGroupItem
                button
                class="d-flex"
                :class="{
                    current: invocation.id === currentItemId,
                    'panel-item': props.inPanel,
                }"
                :active="invocation.id === currentItemId"
                @click="() => cardClicked(invocation)">
                <div class="overflow-auto w-100">
                    <Heading bold size="text" :icon="faSitemap">
                        <span class="truncate-n-lines three-lines">
                            {{ workflowName(invocation.workflow_id) }}
                        </span>
                    </Heading>
                    <Heading size="text" :icon="faHdd">
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
        </template>

        <template v-slot:loading>
            <p>Loading...</p>
        </template>

        <template v-slot:footer>
            <p>All items loaded</p>
        </template>
    </ScrollList>
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
