<script setup lang="ts">
import { faEye } from "@fortawesome/free-regular-svg-icons";
import { faHdd, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import type { WorkflowInvocation } from "@/api/invocations";
import { getData } from "@/components/Grid/configs/invocations";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import GCard from "@/components/Common/GCard.vue";
import Heading from "@/components/Common/Heading.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

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
    const [data, totalMatches] = await getData(offset, limit, "", "create_time", true, extraProps);
    return { items: data, total: totalMatches! };
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

function getInvocationBadges(invocation: WorkflowInvocation) {
    return [
        {
            id: "state",
            label: invocation.state,
            title: invocation.state,
            class: stateClass(invocation.state),
            visible: true,
        },
    ];
}
</script>

<template>
    <ScrollList
        :loader="loadInvocations"
        :item-key="(invocation) => invocation.id"
        :in-panel="inPanel"
        name="invocation"
        name-plural="invocations">
        <template v-slot:item="{ item: invocation }">
            <GCard
                :id="`invocation-${invocation.id}`"
                clickable
                button
                :current="invocation.id === currentItemId"
                :active="invocation.id === currentItemId"
                :badges="getInvocationBadges(invocation)"
                :title="workflowName(invocation.workflow_id)"
                :title-icon="{ icon: faSitemap }"
                title-size="text"
                :update-time="invocation.create_time"
                @title-click="workflowName(invocation.workflow_id)"
                @click="() => cardClicked(invocation)">
                <template v-slot:description>
                    <Heading class="m-0" size="text">
                        <FontAwesomeIcon :icon="faHdd" fixed-width />

                        <small class="text-muted truncate-n-lines two-lines">
                            {{ historyName(invocation.history_id) }}
                        </small>
                    </Heading>
                </template>

                <template v-slot:extra-actions>
                    <div v-if="props.inPanel">
                        <FontAwesomeIcon v-if="invocation.id === currentItemId" :icon="faEye" />
                    </div>
                </template>
            </GCard>
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
