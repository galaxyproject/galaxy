<script setup lang="ts">
import {
    faBuilding,
    faFileImport,
    faGlobe,
    faShieldAlt,
    faUser,
    faUserEdit,
    faUsers,
    type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BButton } from "bootstrap-vue";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { type AnyWorkflow, type Creator, hasCreator } from "@/api/workflows";
import { useToast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import { copy } from "@/utils/clipboard";
import { isUrl } from "@/utils/url";

import UtcDate from "@/components/UtcDate.vue";

interface BadgeData {
    name: string;
    url?: string;
    icon: IconDefinition;
    title?: string;
    class?: Record<string, boolean>;
}

interface Props {
    workflow: AnyWorkflow;
    publishedView: boolean;
    noEditTime?: boolean;
    filterable?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "updateFilter", key: string, value: string | boolean): void;
}>();

const router = useRouter();
const userStore = useUserStore();

const publishedTitle = computed(() => {
    if (props.workflow.published && !props.publishedView) {
        return "已发布的工作流" + (props.filterable ? "。点击筛选已发布的工作流" : "");
    } else if (userStore.matchesCurrentUsername(props.workflow.owner)) {
        return "由您发布" + (props.filterable ? "。点击查看您发布的所有工作流" : "");
    } else {
        return (
            `由'${props.workflow.owner}'发布` +
            (props.filterable ? `。点击查看'${props.workflow.owner}'发布的所有工作流` : "")
        );
    }
});

const shared = computed(() => {
    return !userStore.matchesCurrentUsername(props.workflow.owner);
});

const sourceType = computed(() => {
    const { url, trs_server, trs_tool_id } = props.workflow.source_metadata || {};
    const trs = trs_server || trs_tool_id;
    if (url) {
        return "url";
    } else if (trs) {
        return `trs_${trs}`;
    } else {
        return "";
    }
});

const sourceTitle = computed(() => {
    if (sourceType.value.includes("trs")) {
        return `从TRS ID导入（版本：${props.workflow.source_metadata?.trs_version_id}）。点击复制ID`;
    } else if (sourceType.value == "url") {
        return `从${props.workflow.source_metadata?.url}导入。点击复制链接`;
    } else {
        return `从${(props.workflow as any).source_type}导入`;
    }
});

const creatorBadges = computed<BadgeData[] | undefined>(() => {
    if (hasCreator(props.workflow)) {
        return props.workflow.creator
            ?.map((creator: Creator) => {
                if (!creator.name) {
                    return;
                }
                let url: string | undefined;
                let titleEnd = "工作流创建者";

                if (creator.url && isUrl(creator.url)) {
                    url = creator.url;
                }
                const orcidRegex = /^https:\/\/orcid\.org\/\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$/;
                if (creator.identifier && orcidRegex.test(creator.identifier)) {
                    url = creator.identifier;
                    titleEnd = "ORCID 个人资料";
                }

                return {
                    name: creator.name,
                    url,
                    icon: creator.class === "Organization" ? faBuilding : faUserEdit,
                    title: `${url ? "点击查看" : ""}${titleEnd}`,
                    class: { "cursor-pointer": !!url, "outline-badge": !!url },
                };
            })
            .filter((b) => !!b);
    }
    {
        return undefined;
    }
});

const { success } = useToast();

function onCopyLink() {
    if (sourceType.value == "url") {
        copy(props.workflow.source_metadata?.url);
        success("URL已复制");
    } else if (sourceType.value.includes("trs")) {
        copy(props.workflow.source_metadata?.trs_tool_id);
        success("TRS ID已复制");
    }
}

function onViewMySharedByUser() {
    router.push(`/workflows/list_shared_with_me?owner=${props.workflow.owner}`);
    emit("updateFilter", "user", `'${props.workflow.owner}'`);
}

function onViewUserPublished() {
    router.push(`/workflows/list_published?owner=${props.workflow.owner}`);
    emit("updateFilter", "user", `'${props.workflow.owner}'`);
}

function getStepText(steps: number) {
    if (steps === 1) {
        return "1 步骤";
    } else {
        return `${steps} 步骤`;
    }
}
</script>

<template>
    <div class="workflow-indicators">
        <BButton
            v-if="workflow.published && !publishedView"
            v-b-tooltip.noninteractive.hover
            size="sm"
            class="workflow-published-icon inline-icon-button"
            :title="publishedTitle"
            @click="emit('updateFilter', 'published', true)">
            <FontAwesomeIcon :icon="faGlobe" fixed-width />
        </BButton>
        <FontAwesomeIcon
            v-else-if="workflow.published"
            v-b-tooltip.noninteractive.hover
            title="已发布的工作流"
            :icon="faGlobe"
            fixed-width
            size="sm" />

        <BButton
            v-if="sourceType.includes('trs')"
            v-b-tooltip.noninteractive.hover
            size="sm"
            class="workflow-trs-icon inline-icon-button"
            :title="sourceTitle">
            <FontAwesomeIcon :icon="faShieldAlt" fixed-width @click="onCopyLink" />
        </BButton>

        <BButton
            v-if="sourceType == 'url'"
            v-b-tooltip.noninteractive.hover
            size="sm"
            class="workflow-external-link inline-icon-button"
            :title="sourceTitle">
            <FontAwesomeIcon :icon="faFileImport" fixed-width @click="onCopyLink" />
        </BButton>

        <span v-if="!noEditTime" class="mr-1">
            <small>
                编辑于
                <UtcDate :date="workflow.update_time" mode="elapsed" />
            </small>
        </span>

        <BBadge v-if="workflow.number_of_steps" pill class="mr-1 step-count">
            {{ getStepText(workflow.number_of_steps) }}
        </BBadge>

        <BBadge
            v-if="shared && !publishedView"
            v-b-tooltip.noninteractive.hover
            class="outline-badge cursor-pointer mx-1"
            :title="`'${workflow.owner}' 与你共享了此工作流。点击查看 '${workflow.owner}' 与你共享的所有工作流`"
            @click="onViewMySharedByUser">
            <FontAwesomeIcon :icon="faUsers" size="sm" fixed-width />
            <span class="font-weight-bold"> {{ workflow.owner }} </span>
        </BBadge>

        <BBadge
            v-if="publishedView && workflow.published"
            v-b-tooltip.noninteractive.hover
            data-description="published owner badge"
            class="outline-badge cursor-pointer mx-1"
            :title="publishedTitle"
            @click="onViewUserPublished">
            <FontAwesomeIcon :icon="faUser" size="sm" fixed-width />
            <span class="font-weight-bold"> {{ workflow.owner }} </span>
        </BBadge>

        <template v-if="creatorBadges?.length">
            <BBadge
                v-for="creator in creatorBadges"
                :key="creator.name"
                v-b-tooltip.noninteractive.hover
                data-description="external creator badge"
                class="mx-1"
                :class="creator.class"
                :title="creator.title"
                :href="creator.url"
                target="_blank">
                <FontAwesomeIcon :icon="creator.icon" size="sm" fixed-width />
                <span class="font-weight-bold"> {{ creator.name }} </span>
            </BBadge>
        </template>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-indicators {
    display: flex;
    align-items: center;
}

.step-count {
    display: grid;
    place-items: center;
    height: 1rem;
}
</style>
