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
    username?: string;
    email_hash?: string;
    tags?: string[];
    title?: string;
}

interface Props {
    item?: Item;
}

const props = defineProps<Props>();

const modelTitle = computed(() => {
    const modelClass = props.item?.model_class ?? "Item";
    if (modelClass == "StoredWorkflow") {
        return "Workflow";
    }
    return modelClass;
});

const plural = computed(() => {
    if (modelTitle.value === "History") {
        return "Histories";
    }
    return `${modelTitle.value}s`;
});

const gravatarSource = computed(() => `https://secure.gravatar.com/avatar/${props.item?.email_hash}?d=identicon`);
const owner = computed(() => props.item?.owner ?? props.item?.username ?? "Unavailable");
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
                <h1 class="h-sm">About this {{ modelTitle }}</h1>

                <h2 class="h-md text-break">{{ props.item?.title ?? props.item?.name }}</h2>

                <img :src="gravatarSource" alt="user avatar" />

                <StatelessTags v-if="props.item?.tags" class="tags mt-2" :value="props.item.tags" disabled />

                <br />

                <h2 class="h-sm">Author</h2>

                <div>{{ owner }}</div>

                <hr />

                <h2 class="h-sm">Related Pages</h2>

                <div>
                    <router-link :to="urlAll">All published {{ plural }}</router-link>
                </div>

                <div>
                    <router-link :to="publishedByUser"> Published {{ plural }} by {{ owner }}</router-link>
                </div>
            </div>
            <LoadingSpan v-else message="Loading item details" />

            <div class="flex-fill" />
        </FlexPanel>
    </div>
</template>
