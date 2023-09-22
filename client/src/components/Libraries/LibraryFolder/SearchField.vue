<template>
    <b-input-group size="sm">
        <b-form-input
            id="filterInput"
            v-model="search"
            class="mr-1"
            type="search"
            :placeholder="titleSearch"
            @keyup.enter="startSearch()" />
    </b-input-group>
</template>

<script>
import _l from "utils/localization";

export default {
    name: "SearchField",
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
