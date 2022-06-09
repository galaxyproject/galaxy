<template>
    <span class="stored-how" v-b-tooltip.hover :title="title">{{ text }}</span>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
Vue.use(BootstrapVue);

export default {
    props: {
        isPrivate: {
            // private is reserved word
            type: Boolean,
        },
    },
    computed: {
        text() {
            return this.isPrivate ? "private" : "unrestricted";
        },
        title() {
            if (this.isPrivate) {
                return "This dataset is stored on storage restricted to a single user. It can not be shared, pubished, or added to Galaxy data libraries.";
            } else {
                return "This dataset is stored on unrestricted storage. With sufficient Galaxy permissions, this dataset can be published, shared, or added to Galaxy data libraries.";
            }
        },
    },
};
</script>

<style scoped>
/* Give visual indication of mouseover info */
.stored-how {
    text-decoration-line: underline;
    text-decoration-style: dashed;
}
</style>
