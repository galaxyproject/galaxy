<template>
    <div id="columns">
        <div id="center">
            <div class="center-container">
                <div class="center-panel" style="display: block">
                    <slot />
                </div>
            </div>
        </div>
        <div id="right" class="published-about">
            <div class="unified-panel-header" unselectable="on">
                <div class="unified-panel-header-inner">About this page</div>
            </div>
            <h4>Author</h4>
            <div>{{ details.username }}</div>
            <h4>Related Pages</h4>
            <router-link to="/pages/list_published">All published pages</router-link>
            <router-link :to="publishedByUser">Published pages by {{ details.username }}</router-link>
            <div>{{ details.username }}</div>
            {{ details }}
            <hr/>
        </div>
    </div>
</template>

<script>
export default {
    props: {
        details: {
            type: Object,
            default: () => ({}),
        },
    },
    computed: {
        gravatar() {
            return `https://secure.gravatar.com/avatar/aysam.guerler@gmail.com?d=identicon`;
        },
        publishedByUser() {
            return `/pages/list_published?f-username=${this.details.username}`;
        }
    },
};
</script>
<style scoped>
.published-about {
    padding: 1rem;
    > h3, > h4 {
        margin-bottom: 1rem;
    }
}
</style>