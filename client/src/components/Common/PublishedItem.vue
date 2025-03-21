<script setup lang="ts">
import { computed } from "vue";

import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

interface Item {
    name: string;
    model_class?: string;
    owner?: string;
    username?: string | null;
    email_hash?: string;
    author_deleted?: boolean;
    tags?: string[];
    title?: string;
}

interface Props {
    item?: Item;
}

const props = defineProps<Props>();

const modelTitle = computed(() => {
    const modelClass = props.item?.model_class ?? "项目";
    if (modelClass == "StoredWorkflow") {
        return "工作流";
    }
    return modelClass;
});

const plural = computed(() => {
    return `历史记录`;
});

const owner = computed(() => {
    if (props.item?.author_deleted) {
        return "已归档的作者";
    }
    return props.item?.owner ?? props.item?.username ?? "不可用";
});

const gravatarSource = computed(() => `https://secure.gravatar.com/avatar/${props.item?.email_hash}?d=identicon`);
const pluralPath = computed(() => plural.value.toLowerCase());
const publishedByUser = computed(() => `/${pluralPath.value}/list_published?f-username=${owner.value}`);
const urlAll = computed(() => `/${pluralPath.value}/list_published`);
</script>

<template>
    <div id="columns" class="d-flex">
        <ActivityBar />

        <div id="center" class="m-3 w-100 overflow-auto d-flex flex-column">
            <slot />
        </div>

        <FlexPanel side="right">
            <div v-if="modelTitle" class="m-3">
                <h1 class="h-sm">关于这个 {{ modelTitle }}</h1>

                <h2 class="h-md text-break">{{ props.item?.title ?? props.item?.name }}</h2>

                <img :src="gravatarSource" alt="用户头像" />

                <StatelessTags v-if="props.item?.tags" class="tags mt-2" :value="props.item.tags" disabled />

                <br />

                <h2 class="h-sm">作者</h2>

                <div>{{ owner }}</div>

                <hr />

                <h2 class="h-sm">相关页面</h2>

                <div>
                    <router-link :to="urlAll">所有发布的 {{ plural }}</router-link>
                </div>

                <div v-if="!props.item?.author_deleted">
                    <router-link :to="publishedByUser"> 发布的 {{ plural }} 由 {{ owner }}</router-link>
                </div>
            </div>
            <LoadingSpan v-else message="加载项目信息" />

            <div class="flex-fill" />
        </FlexPanel>
    </div>
</template>