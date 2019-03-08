<template>
    <div class="nametags" :title="title"><nametag v-for="tag in observedTags" :key="tag" :tag="tag" /></div>
</template>

<script>

import { mapActions } from "vuex";
import Nametag from "./Nametag";

export default {
    components: {
        Nametag
    },
    props: {
        storeKey: { type: String, required: true },
        tags: { type: Array, required: false, default: () => [] }
    },
    computed: {
        observedTags() {
            return this.$store.getters.getTagsById(this.storeKey);
        },
        title() {
            return `${this.observedTags.length} nametags`;
        }
    },
    methods: {
        ...mapActions(["updateTags"]),

        scrubTag(tag) {
            let result = tag;
            if (result.startsWith("name:")) {
                result = result.slice(5);
            }
            return result.trim();
        }
    },

    mounted() {
        let cleanTags = this.tags.map(this.scrubTag).filter(t => t.length)
        if (cleanTags.length) {
            this.updateTags({ 
                key: this.storeKey, 
                tags: cleanTags
            });
        }
    }
}

</script>

<style lang="css">

.nametags:empty {
    display: none;
}

.nametags .badge {
    display: inline-block;
    margin-right: 2px;
}

</style>