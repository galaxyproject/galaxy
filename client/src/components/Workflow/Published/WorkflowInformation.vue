<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBuilding, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { RouterLink } from "vue-router";

import { type StoredWorkflowDetailed } from "@/api/workflows";
import { useUserStore } from "@/stores/userStore";
import { getFullAppUrl } from "@/utils/utils";

import Heading from "@/components/Common/Heading.vue";
import CopyToClipboard from "@/components/CopyToClipboard.vue";
import License from "@/components/License/License.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

library.add(faBuilding, faUser);

interface Props {
    workflowInfo: StoredWorkflowDetailed;
    embedded?: boolean;
}

const props = defineProps<Props>();

const userStore = useUserStore();

const gravatarSource = computed(
    () => `https://secure.gravatar.com/avatar/${props.workflowInfo?.email_hash}?d=identicon`
);

const publishedByUser = computed(() => `/workflows/list_published?owner=${props.workflowInfo?.owner}`);

const relativeLink = computed(() => {
    return `/published/workflow?id=${props.workflowInfo.id}`;
});

const fullLink = computed(() => {
    return getFullAppUrl(relativeLink.value.substring(1));
});

const userOwned = computed(() => {
    return userStore.matchesCurrentUsername(props.workflowInfo.owner);
});

const owner = computed(() => {
    if (props.workflowInfo?.creator_deleted) {
        return "已归档作者";
    }
    return props.workflowInfo.owner;
});
</script>

<template>
    <aside class="workflow-information">
        <hgroup>
            <Heading h2 size="xl" class="mb-0">关于此工作流</Heading>
            <span class="ml-2">
                <span data-description="workflow name"> {{ workflowInfo.name }} </span> - 版本
                {{ workflowInfo.version }}
            </span>
        </hgroup>

        <div class="workflow-info-box">
            <hgroup class="mb-2">
                <Heading h3 size="md" class="mb-0">作者</Heading>
                <span class="ml-2">{{ owner }}</span>
            </hgroup>

            <img alt="用户头像" :src="gravatarSource" class="mb-2" />

            <RouterLink
                v-if="!props.workflowInfo?.creator_deleted"
                :to="publishedByUser"
                :target="props.embedded ? '_blank' : ''">
                查看 {{ workflowInfo.owner }} 的所有已发布工作流
            </RouterLink>
        </div>

        <div v-if="workflowInfo?.creator" class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">创建者</Heading>

            <ul class="list-unstyled mb-0">
                <li v-for="(creator, index) in workflowInfo.creator" :key="index">
                    <FontAwesomeIcon v-if="creator.class === 'Person'" icon="fa-user" />
                    <FontAwesomeIcon v-if="creator.class === 'Organization'" icon="fa-building" />
                    {{ creator.name }}
                </li>
            </ul>
        </div>

        <div class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">描述</Heading>

            <p v-if="workflowInfo.annotation" class="mb-0">
                {{ workflowInfo.annotation }}
            </p>
            <p v-else class="mb-0">此工作流没有描述。</p>
        </div>

        <div v-if="workflowInfo?.tags" class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">标签</Heading>

            <StatelessTags class="tags mt-2" :value="workflowInfo.tags" disabled />
        </div>

        <div class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">许可证</Heading>

            <License v-if="workflowInfo.license" :license-id="workflowInfo.license" />
            <span v-else>未指定许可证</span>
        </div>

        <div class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">最后更新</Heading>

            <UtcDate :date="workflowInfo.update_time" mode="pretty" />
        </div>

        <div v-if="!props.embedded && (workflowInfo.published || userOwned)" class="workflow-info-box">
            <Heading h3 size="md" class="mb-0">分享</Heading>

            <span v-if="workflowInfo.published">
                使用以下链接分享此工作流预览：

                <a :href="fullLink" target="_blank">{{ fullLink }}</a>
                <CopyToClipboard message="链接已复制到剪贴板" :text="fullLink" title="复制链接" />。在
                <RouterLink :to="`/workflows/sharing?id=${workflowInfo.id}`">此处</RouterLink>管理分享设置。
            </span>

            <span v-else-if="userOwned">
                此工作流未发布，无法分享。
                <RouterLink :to="`/workflows/sharing?id=${workflowInfo.id}`">发布此工作流</RouterLink>
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
