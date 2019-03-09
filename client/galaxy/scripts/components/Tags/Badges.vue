<template>
    <div class="nametags" :title="title">
        <badge v-for="tag in tags" :key="tag" :tag="tag" />
    </div>
</template>

<script>

import Badge from "./Badge";

export default {
    components: {
        Badge
    },
    props: {
        tags: { type: Array, required: false, default: () => [] }
    },
    computed: {
        title() {
            return `${this.tags.length} nametags`;
        }
    }
}

</script>

<style lang="scss">

/*
.nametags:empty {
    display: none;
}
*/

.nametags .badge {
    display: inline-block;
    margin-right: 2px;
}

</style>
