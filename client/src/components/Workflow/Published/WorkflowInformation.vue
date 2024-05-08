<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBuilding, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { getAppRoot } from "@/onload/loadConfig";
import { useUserStore } from "@/stores/userStore";

import Heading from "@/components/Common/Heading.vue";
import CopyToClipboard from "@/components/CopyToClipboard.vue";
import License from "@/components/License/License.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

library.add(faBuilding, faUser);

interface WorkflowInformation {
    name: string;
    [key: string]: unknown;
    update_time: string;
    license?: string;
    tags?: string[];
    creator?: {
        [key: string]: unknown;
    }[];
}

interface Props {
    workflowInfo: WorkflowInformation;
    embedded?: boolean;
}

const props = defineProps<Props>();

const userStore = useUserStore();

const gravatarSource = computed(
    () => `https://secure.gravatar.com/avatar/${props.workflowInfo?.email_hash}?d=identicon`
);

const publishedByUser = computed(() => `/workflows/list_published?owner=${props.workflowInfo?.owner}`);

const root = computed(() => {
    const port = window.location.port ? `:${window.location.port}` : "";
    return `${window.location.protocol}//${window.location.hostname}${port}${getAppRoot()}`;
});

const relativeLink = computed(() => {
    return `/published/workflow?id=${props.workflowInfo.id}`;
});

const fullLink = computed(() => {
    return `${root.value}${relativeLink.value.substring(1)}`;
});

const userOwned = computed(() => {
    if (userStore.currentUser) {
        return userStore.currentUser.username === props.workflowInfo.owner;
    } else {
        return false;
    }
});
</script>

<template>
    <aside class="workflow-information">
        <hgroup>
            <Heading h2 size="xl" class="mb-0">About This Workflow</Heading>
            <span class="ml-2">
                <span data-description="workflow name"> {{ workflowInfo.name }} </span> - Version
                {{ workflowInfo.version }}
            </span>
        </hgroup>

        <div class="workflow-info-box">
            <hgroup class="mb-2">
                <Heading h3 size="md" class="mb-0">Author</Heading>
                <span class="ml-2">{{ workflowInfo.owner }}</span>
            </hgroup>

            <img alt="User Avatar" :src="gravatarSource" class="mb-2" />

            <router-link :to="publishedByUser" :target="props.embedded ? '_blank' : ''">
                All published Workflows by {{ workflowInfo.owner }}
            </router-link>
        </div>

        <div v-if="workflowInfo?.creator" class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">Creators</Heading>

            <ul class="list-unstyled mb-0">
                <li v-for="(creator, index) in workflowInfo.creator" :key="index">
                    <FontAwesomeIcon v-if="creator.class === 'Person'" icon="fa-user" />
                    <FontAwesomeIcon v-if="creator.class === 'Organization'" icon="fa-building" />
                    {{ creator.name }}
                </li>
            </ul>
        </div>

        <div class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">Description</Heading>

            <p v-if="workflowInfo.annotation" class="mb-0">
                {{ workflowInfo.annotation }}
            </p>
            <p v-else class="mb-0">This Workflow has no description.</p>
        </div>

        <div v-if="workflowInfo?.tags" class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">Tags</Heading>

            <StatelessTags class="tags mt-2" :value="workflowInfo.tags" disabled />
        </div>

        <div class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">License</Heading>

            <License v-if="workflowInfo.license" :license-id="workflowInfo.license" />
            <span v-else>No License specified</span>
        </div>

        <div class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">Last Updated</Heading>

            <UtcDate :date="workflowInfo.update_time" mode="pretty" />
        </div>

        <div v-if="!props.embedded && (workflowInfo.published || userOwned)" class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">Sharing</Heading>

            <span v-if="workflowInfo.published">
                Use the following link to share preview of this workflow:

                <a :href="fullLink" target="_blank">{{ fullLink }}</a>
                <CopyToClipboard message="Link copied to clipboard" :text="fullLink" title="Copy link" />
            </span>

            <span v-else-if="userOwned">
                This workflow is not published and cannot be shared.
                <router-link :to="`/workflows/sharing?id=${workflowInfo.id}`">Publish this workflow</router-link>
            </span>
        </div>
    </aside>
</template>

<style scoped lang="scss">
.workflow-information {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
    justify-content: flex-start;
    align-self: flex-start;
    overflow-y: scroll;

    .workflow-info-box {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }
}
</style>
