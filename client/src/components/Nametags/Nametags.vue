<template>
    <div class="nametags" :title="title"><nametag v-for="tag in nameTags" :key="tag" :tag="tag" /></div>
</template>

<script>
import Nametag from "./Nametag";
import { mapActions } from "vuex";

export default {
    components: {
        Nametag,
    },
    props: {
        storeKey: { type: String, required: true },
        tags: { type: Array, required: false, default: () => [] },
    },
    computed: {
        // only display tags that start with name:
        nameTags() {
            return this.$store.getters.getTagsById(this.storeKey).filter((tag) => tag.startsWith("name:"));
        },
        title() {
            return `${this.nameTags.length} nametags`;
        },
    },
    methods: {
        ...mapActions(["updateTags", "initializeTags"]),
    },
    mounted() {
        this.initializeTags({ key: this.storeKey, tags: this.tags });
    },
};
</script>

<style lang="scss">
.nametags:empty {
    display: none;
}

.nametags .badge {
    display: inline-block;
    margin-right: 2px;
}
</style>
