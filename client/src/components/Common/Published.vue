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
                <div v-if="modelClass">
                    <h3>About this {{ modelClass }}</h3>
                    <br />
                    <h4>Author</h4>
                    <div>{{ details.username }}</div>
                    <br />
                    <h4>Related Pages</h4>
                    <div>
                        <router-link to="/pages/list_published"> All published {{ plural }} </router-link>
                    </div>
                    <div>
                        <router-link :to="publishedByUser">
                            Published {{ plural }} by {{ details.username }}
                        </router-link>
                    </div>
                    <hr />
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
        publishedByUser() {
            return `/pages/list_published?f-username=${this.details.username}`;
        },
        modelClass() {
            return this.details && this.details.model_class;
        },
        plural() {
            const modelLower = this.modelClass.toLowerCase();
            if (modelLower == "history") {
                return "histories";
            }
            return `${modelLower}s`;
        },
    },
    created() {
        console.log(this.details);
    },
};
</script>
