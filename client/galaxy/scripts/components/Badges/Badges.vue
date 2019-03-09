<template>
    <div class="nametags" :title="title">
        <badge v-for="tag in observedTags" :key="tag" :tag="tag" />
    </div>
</template>

<script>

import Badge from "./Badge";
import { mapActions } from "vuex";

export default {
    components: {
        Badge
    },
    props: {
        storeKey: { type: String, required: true },
        tags: { type: Array, required: false, default: () => [] }
    },
    computed: {
        observedTags: {
            get() {
                return this.$store.getters.getTagsById(this.storeKey);
            },
            set(tags) {
                this.updateTags({ key: this.storeKey, tags });
            }
        },
        title() {
            return `${this.observedTags.length} nametags`;
        }
    },
    methods: {
        ...mapActions(["updateTags", "initializeTags"])
    },
    mounted() {
        this.initializeTags({ key: this.storeKey, tags: this.tags });
    }
}

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
