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
        return "Published workflow" + (props.filterable ? ". Click to filter published workflows" : "");
    } else if (userStore.matchesCurrentUsername(props.workflow.owner)) {
        return "Published by you" + (props.filterable ? ". Click to view all published workflows by you" : "");
    } else {
        return (
            `Published by '${props.workflow.owner}'` +
            (props.filterable ? `. Click to view all published workflows by '${props.workflow.owner}'` : "")
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
        return `Imported from TRS ID (version: ${props.workflow.source_metadata?.trs_version_id}). Click to copy ID`;
    } else if (sourceType.value == "url") {
        return `Imported from ${props.workflow.source_metadata?.url}. Click to copy link`;
    } else {
        return `Imported from ${(props.workflow as any).source_type}`;
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
                let titleEnd = "Workflow Creator";

                if (creator.url && isUrl(creator.url)) {
                    url = creator.url;
                }
                const orcidRegex = /^https:\/\/orcid\.org\/\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$/;
                if (creator.identifier && orcidRegex.test(creator.identifier)) {
                    url = creator.identifier;
                    titleEnd = "ORCID profile";
                }

                return {
                    name: creator.name,
                    url,
                    icon: creator.class === "Organization" ? faBuilding : faUserEdit,
                    title: `${url ? "Click to view " : ""}${titleEnd}`,
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
        success("URL copied");
    } else if (sourceType.value.includes("trs")) {
        copy(props.workflow.source_metadata?.trs_tool_id);
        success("TRS ID copied");
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
        return "1 step";
    } else {
        return `${steps} steps`;
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
            title="Published workflow"
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
                edited
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
            :title="`'${workflow.owner}' shared this workflow with you. Click to view all workflows shared with you by '${workflow.owner}'`"
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
