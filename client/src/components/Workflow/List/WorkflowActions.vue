<script setup lang="ts">
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";
import {
    faCaretDown,
    faCopy,
    faDownload,
    faExternalLinkAlt,
    faFileExport,
    faLink,
    faPlay,
    faShareAlt,
    faSpinner,
    faStar,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BDropdown, BDropdownItem } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { type AnyWorkflow, hasVersion } from "@/api/workflows";
import { useUserStore } from "@/stores/userStore";

import { useWorkflowActions } from "./useWorkflowActions";

interface Props {
    workflow: AnyWorkflow;
    published?: boolean;
    editor?: boolean;
    current?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    published: false,
    editor: false,
    current: false,
});

const emit = defineEmits<{
    (e: "refreshList", overlayLoading?: boolean): void;
    (e: "dropdown", open: boolean): void;
}>();

const { bookmarkLoading, deleteWorkflow, toggleBookmark, copyPublicLink, copyWorkflow, downloadUrl } =
    useWorkflowActions(
        computed(() => props.workflow),
        () => emit("refreshList", true)
    );

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const shared = computed(() => {
    return !userStore.matchesCurrentUsername(props.workflow.owner);
});

const sourceType = computed(() => {
    if (props.workflow.source_metadata?.url) {
        return "url";
    } else if (props.workflow.source_metadata?.trs_server) {
        return `trs_${props.workflow.source_metadata?.trs_server}`;
    } else {
        return "";
    }
});

const runPath = computed(
    () =>
        `/workflows/run?id=${props.workflow.id}${
            hasVersion(props.workflow) ? `&version=${props.workflow.version}` : ""
        }`
);

const dockstoreUrl = computed(() => {
    const trsId = props.workflow?.source_metadata?.trs_tool_id as string | undefined;
    if (trsId) {
        return `https://dockstore.org/workflows${trsId.slice(9)}`;
    } else {
        return undefined;
    }
});
</script>

<template>
    <div class="workflow-actions">
        <BButtonGroup>
            <BButton
                v-if="!props.workflow.deleted && !props.workflow.show_in_tool_panel"
                v-b-tooltip.hover.noninteractive
                class="workflow-bookmark-button-add inline-icon-button"
                variant="link"
                title="添加到书签"
                tooltip="添加到书签。此工作流将显示在左侧工具面板中。"
                size="sm"
                @click="toggleBookmark(true)">
                <FontAwesomeIcon v-if="!bookmarkLoading" :icon="farStar" fixed-width />
                <FontAwesomeIcon v-else :icon="faSpinner" spin fixed-width />
            </BButton>
            <BButton
                v-else-if="!props.workflow.deleted && props.workflow.show_in_tool_panel"
                v-b-tooltip.hover.noninteractive
                class="workflow-bookmark-button-remove inline-icon-button"
                variant="link"
                title="移除书签"
                size="sm"
                @click="toggleBookmark(false)">
                <FontAwesomeIcon v-if="!bookmarkLoading" :icon="faStar" fixed-width />
                <FontAwesomeIcon v-else :icon="faSpinner" spin fixed-width />
            </BButton>

            <BDropdown
                v-b-tooltip.top.noninteractive
                :data-workflow-actions-dropdown="workflow.id"
                right
                no-caret
                class="workflow-actions-dropdown"
                title="工作流操作"
                toggle-class="inline-icon-button"
                variant="link"
                @show="() => emit('dropdown', true)"
                @hide="() => emit('dropdown', false)">
                <template v-slot:button-content>
                    <FontAwesomeIcon :icon="faCaretDown" fixed-width />
                </template>

                <template v-if="props.editor">
                    <BDropdownItem :to="runPath" title="运行工作流" size="sm" variant="link">
                        <FontAwesomeIcon :icon="faPlay" fixed-width />
                        运行
                    </BDropdownItem>

                    <BDropdownItem
                        v-if="props.workflow.published"
                        size="sm"
                        title="复制工作流链接"
                        @click="copyPublicLink">
                        <FontAwesomeIcon :icon="faLink" fixed-width />
                        工作流链接
                    </BDropdownItem>

                    <BDropdownItem v-if="!isAnonymous && !shared" size="sm" title="复制工作流" @click="copyWorkflow">
                        <FontAwesomeIcon :icon="faCopy" fixed-width />
                        复制
                    </BDropdownItem>

                    <BDropdownItem
                        size="sm"
                        title="以.ga格式下载工作流"
                        target="_blank"
                        :href="downloadUrl">
                        <FontAwesomeIcon :icon="faDownload" fixed-width />
                        下载
                    </BDropdownItem>

                    <BDropdownItem
                        v-if="!isAnonymous && !shared"
                        size="sm"
                        title="分享"
                        :to="`/workflows/sharing?id=${workflow.id}`">
                        <FontAwesomeIcon :icon="faShareAlt" fixed-width />
                        分享
                    </BDropdownItem>
                </template>

                <BDropdownItem
                    v-if="!isAnonymous && !shared && !props.workflow.deleted && !props.current"
                    class="workflow-delete-button"
                    title="删除工作流"
                    size="sm"
                    @click="deleteWorkflow">
                    <FontAwesomeIcon :icon="faTrash" fixed-width />
                    删除
                </BDropdownItem>

                <BDropdownItem
                    v-if="sourceType.includes('trs')"
                    class="source-trs-button"
                    :title="`在 ${props.workflow.source_metadata?.trs_server} 上查看`"
                    size="sm"
                    :href="dockstoreUrl"
                    target="_blank">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                    在Dockstore上查看
                </BDropdownItem>

                <BDropdownItem
                    v-if="sourceType == 'url'"
                    class="workflow-view-external-link-button"
                    title="查看外部链接"
                    size="sm"
                    :href="props.workflow.source_metadata?.url"
                    target="_blank">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                    查看外部链接
                </BDropdownItem>

                <BDropdownItem
                    v-if="!props.workflow.deleted"
                    class="workflow-export-button"
                    title="导出"
                    size="sm"
                    :to="`/workflows/export?id=${props.workflow.id}`">
                    <FontAwesomeIcon :icon="faFileExport" fixed-width />
                    导出
                </BDropdownItem>
            </BDropdown>
        </BButtonGroup>
    </div>
</template>

<style scoped lang="scss">
.workflow-actions {
    display: flex;
    align-items: center;
}
</style>
