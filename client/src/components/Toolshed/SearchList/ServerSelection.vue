<template>
    <div v-if="!loading" class="m-1 text-muted">
        <span class="description"> {{ total }} repositories available at </span>
        <span v-if="showDropdown" class="dropdown">
            <BLink
                id="dropdownToolshedUrl"
                data-toggle="dropdown"
                aria-haspopup="true"
                aria-expanded="false"
                class="font-weight-bold">
                {{ toolshedUrl }}
                <span class="fa fa-caret-down" />
            </BLink>
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
            <BLink :href="toolshedUrl" target="_blank" class="font-weight-bold">
                {{ toolshedUrl }}
            </BLink>
        </span>
    </div>
</template>
<script>
import { BLink } from "bootstrap-vue";

export default {
    components: { BLink },
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
