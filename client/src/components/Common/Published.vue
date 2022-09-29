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
                    <h4>About this {{ modelTitle }}</h4>
                    <h3>{{ details.title }}</h3>
                    <br />
                    <h4>Author</h4>
                    <div>{{ owner }}</div>
                    <br />
                    <hr />
                    <h4>Related Pages</h4>
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
import LoadingSpan from "components/LoadingSpan";
export default {
    components: {
        LoadingSpan,
    },
    props: {
        details: {
            type: Object,
            default: () => ({}),
        },
    },
    watch: {
        details() {
            console.log(this.details);
        },
    },
    computed: {
        gravatar() {
            return `https://secure.gravatar.com/avatar/aysam.guerler@gmail.com?d=identicon`;
        },
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
    created() {
        console.log(this.details);
    },
};
</script>
