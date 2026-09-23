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

function repField(tool: UnprivilegedToolResponse, key: string): string | undefined {
    // representation may be a typed UserToolSource (status ok/lifted) or a raw
    // dict (status invalid). Both shapes still hold name/id/etc by string key,
    // but the union type loses property access — read defensively.
    const rep = tool.representation as Record<string, unknown> | undefined;
    const value = rep?.[key];
    return typeof value === "string" ? value : undefined;
}

function cardClicked(tool: UnprivilegedToolResponse) {
    if (props.inPanel) {
        emit("unprivileged-tool-clicked", tool);
    }
    if (props.inWorkflowEditor) {
        emit("onInsertTool", repField(tool, "id"), repField(tool, "name"), tool.uuid);
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
    const badges = [
        {
            id: "version",
            label: repField(tool, "version") ?? "",
            title: "Version of this custom tool",
        },
    ];
    if (tool.representation_status === "lifted") {
        badges.push({
            id: "status",
            label: "needs update",
            title:
                "This tool's stored definition uses conventions that are no longer valid; " +
                "they are ignored on read. Re-save the tool to clean it up.",
        });
    } else if (tool.representation_status === "invalid") {
        badges.push({
            id: "status",
            label: "schema error",
            title:
                "This tool's stored definition does not satisfy the current schema. " +
                "Open it in the editor to repair.",
        });
    }
    return badges;
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
                    :title="repField(tool, 'name') ?? tool.uuid"
                    :title-icon="{ icon: faWrench }"
                    title-size="text"
                    :update-time="tool.create_time"
                    @title-click="cardClicked(tool)"
                    @click="() => cardClicked(tool)">
                    <template v-slot:description>
                        <Heading class="m-0" size="text">
                            <small class="text-muted truncate-n-lines two-lines">
                                {{ repField(tool, "description") }}
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
