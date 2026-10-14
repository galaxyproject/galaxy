<template>
    <BInputGroup size="sm">
        <BFormInput
            id="filterInput"
            v-model="search"
            class="mr-1"
            type="search"
            :placeholder="titleSearch"
            @keyup.enter="startSearch()" />
    </BInputGroup>
</template>

<script>
import { BFormInput, BInputGroup } from "bootstrap-vue";

import _l from "@/utils/localization";

export default {
    name: "SearchField",
    components: { BFormInput, BInputGroup },
    props: {
        typingDelay: {
            type: Number,
            default: 1000,
            required: false,
        },
    },
    data() {
        return {
            search: "",
            awaitingSearch: false,
            titleSearch: _l("Search"),
        };
    },
    watch: {
        search: function () {
            if (!this.awaitingSearch) {
                setTimeout(() => {
                    this.startSearch();
                }, this.typingDelay);
            }
            this.awaitingSearch = true;
        },
    },
    methods: {
        startSearch() {
            this.$emit("updateSearch", this.search);
            this.awaitingSearch = false;
        },
    },
};
</script>

<style scoped></style>
