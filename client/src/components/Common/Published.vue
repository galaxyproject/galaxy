<template>
    <div id="columns">
        <div id="center">
            <div class="center-container">
                <div class="center-panel" style="display: block">
                    <slot />
                </div>
            </div>
        </div>
        <div id="right">
            <div class="m-3">
                <div v-if="modelTitle">
                    <h1 class="h-sm">About this {{ modelTitle }}</h1>
                    <h2 class="h-md">{{ details.title || details.name }}</h2>
                    <StatelessTags v-if="details.tags" class="tags mt-2" :value="details.tags" :disabled="true" />
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
                <LoadingSpan v-else message="Loading details" />
            </div>
        </div>
    </div>
</template>

<script>
import { StatelessTags } from "components/Tags";
import LoadingSpan from "components/LoadingSpan";
export default {
    components: {
        LoadingSpan,
        StatelessTags,
    },
    props: {
        details: {
            type: Object,
            required: true,
        },
    },
    computed: {
        modelTitle() {
            const modelClass = this.details ? this.details.model_class : "Item";
            if (modelClass == "StoredWorkflow") {
                return "Workflow";
            }
            return modelClass;
        },
        owner() {
            return this.details.owner || this.details.username || "Unavailable";
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
            return `/${this.pluralPath}/list_published?f-username=${this.details.username}`;
        },
        urlAll() {
            return `/${this.pluralPath}/list_published`;
        },
    },
};
</script>
