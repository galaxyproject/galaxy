<template>
    <div id="columns" class="d-flex">
        <div id="center" class="m-3 w-100 overflow-auto">
            <slot />
        </div>
        <FlexPanel side="right">
            <div v-if="modelTitle" class="m-3">
                <h1 class="h-sm">About this {{ modelTitle }}</h1>
                <h2 class="h-md text-break">{{ item.title || item.name }}</h2>
                <img :src="gravatarSource" alt="user avatar" />
                <StatelessTags v-if="item.tags" class="tags mt-2" :value="item.tags" :disabled="true" />
                <br />
                <h2 class="h-sm">Author</h2>
                <div>{{ owner }}</div>
                <hr />
                <h2 class="h-sm">Related Pages</h2>
                <div>
                    <router-link :to="urlAll">All published {{ plural }}.</router-link>
                </div>
                <div>
                    <router-link :to="publishedByUser"> Published {{ plural }} by {{ owner }}. </router-link>
                </div>
            </div>
            <LoadingSpan v-else message="Loading item details" />
            <div class="flex-fill" />
        </FlexPanel>
    </div>
</template>

<script>
import { StatelessTags } from "components/Tags";
import LoadingSpan from "components/LoadingSpan";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
export default {
    components: {
        FlexPanel,
        LoadingSpan,
        StatelessTags,
    },
    props: {
        item: {
            type: Object,
            required: true,
        },
    },
    computed: {
        gravatarSource() {
            return `https://secure.gravatar.com/avatar/${this.item.email_hash}?d=identicon`;
        },
        modelTitle() {
            const modelClass = this.item ? this.item.model_class : "Item";
            if (modelClass == "StoredWorkflow") {
                return "Workflow";
            }
            return modelClass;
        },
        owner() {
            return this.item.owner || this.item.username || "Unavailable";
        },
        plural() {
            if (this.modelTitle == "History") {
                return "Histories";
            }
            return `${this.modelTitle}s`;
        },
        pluralPath() {
            return this.plural.toLowerCase();
        },
        publishedByUser() {
            return `/${this.pluralPath}/list_published?f-username=${this.owner}`;
        },
        urlAll() {
            return `/${this.pluralPath}/list_published`;
        },
    },
};
</script>
