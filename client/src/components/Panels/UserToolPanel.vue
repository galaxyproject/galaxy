<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye } from "@fortawesome/free-regular-svg-icons";
import { faArrowDown, faInfoCircle, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { GalaxyApi, type MessageException, type UnprivilegedToolResponse } from "@/api";

import ActivityPanel from "./ActivityPanel.vue";
import Heading from "@/components/Common/Heading.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";
import UtcDate from "@/components/UtcDate.vue";

const errorMsg = ref<MessageException | undefined>();

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

library.add(faEye, faArrowDown, faInfoCircle, faPlus);

async function loadUnprivilegedTools(offset: number, limit: number) {
    const { data, error } = await GalaxyApi().GET("/api/unprivileged_tools");
    if (error) {
        errorMsg.value = error;
    } else {
        return {
            items: data,
            total: data.length,
        };
    }
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

function newTool(toolUuid?: string) {
    let route = "/tools/editor";
    if (toolUuid) {
        route = `${route}/${toolUuid}`;
    }
    if (props.inWorkflowEditor && toolUuid) {
        emit("onEditTool");
    }
    if (props.inWorkflowEditor) {
        emit("onCreateTool");
    }
    router.push(route);
}
</script>

<template>
    <ActivityPanel title="Custom Tools">
        <template v-slot:header-buttons>
            <BButtonGroup>
                <BButton
                    v-b-tooltip.bottom.hover
                    data-description="create new custom tool"
                    size="sm"
                    variant="link"
                    title="Create a new custom tool"
                    @click="newTool">
                    <FontAwesomeIcon :icon="faPlus" fixed-width />
                </BButton>
            </BButtonGroup>
        </template>
        <ScrollList :loader="loadUnprivilegedTools" :item-key="(tool) => tool.uuid" :in-panel="inPanel">
            <template v-slot:header>
                <p>Loading...</p>
            </template>
            <template v-slot:item="{ item: tool }">
                <BListGroupItem
                    button
                    class="d-flex"
                    :class="{
                        current: tool.uuid === currentItemId,
                        'panel-item': props.inPanel,
                    }"
                    :active="tool.uuid === currentItemId">
                    <div class="overflow-auto w-100" @click="() => cardClicked(tool)">
                        <Heading bold size="text" icon="fa-wrench">
                            <span class="truncate-n-lines three-lines">
                                {{ tool.representation.name }}
                            </span>
                            <small class="text-muted truncate-n-lines two-lines">
                                {{ tool.representation.description }}
                            </small>
                        </Heading>
                        <div class="d-flex justify-content-between">
                            <BBadge v-b-tooltip.noninteractive.hover pill>
                                <UtcDate :date="tool.create_time" mode="elapsed" />
                            </BBadge>
                            <BBadge v-b-tooltip.noninteractive.hover pill>
                                {{ tool.representation.version }}
                            </BBadge>
                            <BBadge @click.stop="() => newTool(tool.uuid)">
                                <FontAwesomeIcon icon="fa-edit" />
                                <span v-localize>Edit</span>
                            </BBadge>
                        </div>
                    </div>

                    <div v-if="props.inPanel" class="position-absolute mr-3" style="right: 0">
                        <FontAwesomeIcon v-if="tool.id === currentItemId" :icon="faEye" size="lg" />
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
