<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFileImport, faGlobe, faShieldAlt, faUser, faUsers } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BButton } from "bootstrap-vue";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import { copy } from "@/utils/clipboard";

import UtcDate from "@/components/UtcDate.vue";

library.add(faFileImport, faGlobe, faShieldAlt, faUsers, faUser);

interface Props {
    workflow: any;
    publishedView: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update-filter", key: string, value: any): void;
}>();

const router = useRouter();
const userStore = useUserStore();

const publishedTitle = computed(() => {
    if (userStore.matchesCurrentUsername(props.workflow.owner)) {
        return "Published by you. Click to view all published workflows by you";
    } else {
        return `Published by '${props.workflow.owner}'. Click to view all published workflows by '${props.workflow.owner}'`;
    }
});

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

const sourceTitle = computed(() => {
    if (sourceType.value.includes("trs")) {
        return `Imported from TRS ID (version: ${props.workflow.source_metadata.trs_version_id}). Click to copy ID`;
    } else if (sourceType.value == "url") {
        return `Imported from ${props.workflow.source_metadata.url}. Click to copy link`;
    } else {
        return `Imported from ${props.workflow.source_type}`;
    }
});

function onCopyLink() {
    if (sourceType.value == "url") {
        copy(props.workflow.source_metadata.url);
        Toast.success("URL copied");
    } else if (sourceType.value.includes("trs")) {
        copy(props.workflow.source_metadata.trs_tool_id);
        Toast.success("TRS ID copied");
    }
}

function onViewMySharedByUser() {
    router.push(`/workflows/list_shared_with_me?owner=${props.workflow.owner}`);
    emit("update-filter", "user", `'${props.workflow.owner}'`);
}

function onViewUserPublished() {
    router.push(`/workflows/list_published?owner=${props.workflow.owner}`);
    emit("update-filter", "user", `'${props.workflow.owner}'`);
}
</script>

<template>
    <div>
        <BButton
            v-if="workflow.published && !publishedView"
            v-b-tooltip.noninteractive.hover
            size="sm"
            class="workflow-published-icon inline-icon-button"
            title="Published workflow. Click to filter published workflows"
            @click="emit('update-filter', 'published', true)">
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

        <span class="mr-1">
            <small>
                edited
                <UtcDate :date="workflow.update_time" mode="elapsed" />
            </small>
        </span>

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
            v-if="publishedView"
            v-b-tooltip.noninteractive.hover
            class="outline-badge cursor-pointer mx-1"
            :title="publishedTitle"
            @click="onViewUserPublished">
            <FontAwesomeIcon :icon="faUser" size="sm" fixed-width />
            <span class="font-weight-bold"> {{ workflow.owner }} </span>
        </BBadge>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-badge {
    background: $brand-secondary;
    color: $brand-primary;
    border: 1px solid $brand-primary;

    &:hover {
        color: $brand-secondary;
        background: $brand-primary;
    }
}
</style>
