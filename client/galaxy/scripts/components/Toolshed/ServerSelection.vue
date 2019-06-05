<template>
    <div v-if="!loading" class="m-1 text-muted">
        {{ total }} repositories available at
        <span v-if="showDropdown" class="dropdown">
            <b-link id="dropdownToolshedUrl" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                {{ toolshedUrl }}
            </b-link>
            <div class="dropdown-menu" aria-labelledby="dropdownToolshedUrl">
                <a
                    v-for="url in toolshedUrls"
                    :key="url"
                    class="dropdown-item"
                    href="#"
                    @click.prevent="onToolshed(url)"
                    >{{ url }}</a
                >
            </div>
        </span>
        <span v-else>
            <b-link :href="toolshedUrl" target="_blank">
                {{ toolshedUrl }}
            </b-link>
        </span>
    </div>
</template>
<script>
export default {
    props: ["toolshedUrl", "toolshedUrls", "loading", "total"],
    computed: {
        showDropdown() {
            return this.toolshedUrls.length > 1;
        }
    },
    methods: {
        onToolshed(url) {
            this.$emit("onToolshed", url);
        }
    }
};
</script>
