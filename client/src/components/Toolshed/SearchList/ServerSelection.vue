<template>
    <span class="description"> 在以下地址可获取 {{ total }} 个代码库 </span>
        <span v-if="showDropdown" class="dropdown">
            <b-link
                id="dropdownToolshedUrl"
                data-toggle="dropdown"
                aria-haspopup="true"
                aria-expanded="false"
                class="font-weight-bold">
                {{ toolshedUrl }}
                <span class="fa fa-caret-down" />
            </b-link>
            <div class="dropdown-menu" aria-labelledby="dropdownToolshedUrl">
                <a
                    v-for="url in toolshedUrls"
                    :key="url"
                    class="dropdown-item"
                    href="javascript:void(0)"
                    role="button"
                    @click.prevent="onToolshed(url)"
                    >{{ url }}</a
                >
            </div>
        </span>
        <span v-else>
            <b-link :href="toolshedUrl" target="_blank" class="font-weight-bold">
                {{ toolshedUrl }}
            </b-link>
        </span>
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    props: {
        toolshedUrl: {
            type: String,
            required: true,
        },
        toolshedUrls: {
            type: Array,
            required: true,
        },
        loading: {
            type: Boolean,
            required: true,
        },
        total: {
            type: Number,
            required: true,
        },
    },
    computed: {
        showDropdown() {
            return this.toolshedUrls.length > 1;
        },
    },
    methods: {
        onToolshed(url) {
            this.$emit("onToolshed", url);
        },
    },
};
</script>
<style scoped>
span.dropdown {
    display: inline-block;
}
</style>
