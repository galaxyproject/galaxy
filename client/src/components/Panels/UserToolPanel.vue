<script setup lang="ts">
import { faEdit, faPlus, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faCancel } from "font-awesome-6";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import type { UnprivilegedToolResponse } from "@/api";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";

import ActivityPanel from "./ActivityPanel.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import GCard from "@/components/Common/GCard.vue";
import Heading from "@/components/Common/Heading.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

interface Props {
    inPanel?: boolean;
    limit?: number;
    inWorkflowEditor?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    inPanel: false,
    limit: 20,
    inWorkflowEditor: false,
});

const emit = defineEmits(["unprivileged-tool-clicked", "onInsertTool", "onEditTool", "onCreateTool"]);

const unprivilegedToolStore = useUnprivilegedToolStore();
const { unprivilegedTools, canUseUnprivilegedTools } = storeToRefs(unprivilegedToolStore);

async function loadUnprivilegedTools(offset: number, limit: number) {
    return { items: unprivilegedTools.value || [], total: unprivilegedTools.value?.length || 0 };
}
const uuidRegex = /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/;

const route = useRoute();
const router = useRouter();

const currentItemId = computed(() => {
    if (route.query.tool_uuid) {
        return route.query.tool_uuid;
    }
    const path = route.path;
    const match = path.match(uuidRegex);
    return match ? match[0] : undefined;
});

function cardClicked(tool: UnprivilegedToolResponse) {
    if (props.inPanel) {
        emit("unprivileged-tool-clicked", tool);
    }
    if (props.inWorkflowEditor) {
        emit("onInsertTool", tool.representation.id, tool.representation.name, tool.uuid);
    } else {
        router.push(`/?tool_uuid=${tool.uuid}`);
    }
}

function editTool(toolUuid: string) {
    const route = `/tools/editor/${toolUuid}`;
    if (props.inWorkflowEditor && toolUuid) {
        emit("onEditTool");
    }
    router.push(route);
}

function newTool() {
    const route = "/tools/editor";
    if (props.inWorkflowEditor) {
        emit("onCreateTool");
    }
    router.push(route);
}

function getToolBadges(tool: UnprivilegedToolResponse) {
    return [
        {
            id: "version",
            label: tool.representation.version,
            title: "Version of this custom tool",
        },
    ];
}

function getToolSecondaryActions(tool: UnprivilegedToolResponse) {
    return [
        {
            id: "deactivate",
            label: "Deactivate",
            icon: faCancel,
            title: "Deactivate this custom tool",
            handler: () => {
                unprivilegedToolStore.deactivateTool(tool.uuid);
            },
        },
        {
            id: "edit",
            label: "Edit",
            icon: faEdit,
            title: "Edit this custom tool",
            handler: () => editTool(tool.uuid),
        },
    ];
}
</script>

<template>
    <ActivityPanel v-if="canUseUnprivilegedTools" title="Custom Tools">
        <template v-slot:header-buttons>
            <GButtonGroup>
                <GButton
                    data-description="create new custom tool"
                    size="small"
                    tooltip
                    title="Create a new custom tool"
                    transparent
                    @click="newTool">
                    <FontAwesomeIcon :icon="faPlus" fixed-width />
                </GButton>
            </GButtonGroup>
        </template>
        <!-- key ScrollList on length of unprivilegedTools so that we rerender if the tools in the store change-->
        <ScrollList
            :key="unprivilegedTools?.length"
            :loader="loadUnprivilegedTools"
            :item-key="(tool) => tool.uuid"
            :in-panel="inPanel"
            name="custom tool"
            name-plural="custom tools">
            <template v-slot:item="{ item: tool }">
                <GCard
                    :id="`custom-tool-${tool.uuid}`"
                    clickable
                    button
                    :current="tool.uuid === currentItemId"
                    :active="tool.uuid === currentItemId"
                    :badges="getToolBadges(tool)"
                    :secondary-actions="getToolSecondaryActions(tool)"
                    :title="tool.representation.name"
                    :title-icon="{ icon: faWrench }"
                    title-size="text"
                    :update-time="tool.create_time"
                    @title-click="cardClicked(tool)"
                    @click="() => cardClicked(tool)">
                    <template v-slot:description>
                        <Heading class="m-0" size="text">
                            <small class="text-muted truncate-n-lines two-lines">
                                {{ tool.representation.description }}
                            </small>
                        </Heading>
                    </template>
                </GCard>
            </template>
        </ScrollList>
    </ActivityPanel>
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
