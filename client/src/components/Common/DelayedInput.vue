<template>
    <b-input-group>
        <b-input
            ref="toolInput"
            v-model="queryInput"
            class="search-query"
            size="sm"
            autocomplete="off"
            :placeholder="placeholder"
            @input="delayQuery"
            @change="setQuery"
            @keydown.esc="setQuery('')" />
        <b-input-group-append>
            <b-button
                class="search-clear"
                size="sm"
                :title="titleClear | l"
                data-description="reset query"
                @click="clearBox">
                <icon v-if="loading" icon="spinner" spin />
                <icon v-else icon="times" />
            </b-button>
        </b-input-group-append>
    </b-input-group>
</template>
<script>
export default {
    props: {
        query: {
            type: String,
            default: "",
        },
        loading: {
            type: Boolean,
            default: false,
        },
        placeholder: {
            type: String,
            default: "Enter your search term here.",
        },
        delay: {
            type: Number,
            default: 1000,
        },
    },
    data() {
        return {
            queryInput: null,
            queryTimer: null,
            queryCurrent: null,
            titleClear: "clear search (esc)",
        };
    },
    watch: {
        query(queryNew) {
            this.setQuery(queryNew);
        },
    },
    methods: {
        clearTimer() {
            if (this.queryTimer) {
                clearTimeout(this.queryTimer);
            }
        },
        delayQuery(query) {
            this.clearTimer();
            if (query) {
                this.queryTimer = setTimeout(() => {
                    this.setQuery(query);
                }, this.delay);
            } else {
                this.setQuery(query);
            }
        },
        setQuery(queryNew) {
            this.clearTimer();
            if (this.queryCurrent !== this.queryInput || this.queryCurrent !== queryNew) {
                this.queryCurrent = this.queryInput = queryNew;
                this.$emit("change", this.queryCurrent);
            }
        },
        clearBox() {
            this.setQuery("");
            this.$refs.toolInput.focus();
        },
    },
};
</script>
