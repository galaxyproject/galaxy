<template>
    <b-input-group size="sm">
        <b-form-input
            v-model="search"
            class="mr-1"
            input="updateSearch($event)"
            type="search"
            id="filterInput"
            placeholder="Search"
        />
    </b-input-group>
</template>

<script>
export default {
    name: "SearchField",
    data() {
        return {
            search: "",
            awaitingSearch: false,
        };
    },

    watch: {
        search: function () {
            if (!this.awaitingSearch) {
                setTimeout(() => {
                    this.$emit("updateSearch", this.search);
                    this.awaitingSearch = false;
                }, 1000); // 1 sec delay
            }
            this.awaitingSearch = true;
        },
    },
};
</script>

<style scoped></style>
