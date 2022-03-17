<template>
    <div class="search-input">
        <b-input
            class="search-query"
            :placeholder="placeholder"
            v-model="queryInput"
            @input="delayQuery"
            @change="setQuery"
            @keydown.esc="setQuery()" />
        <font-awesome-icon v-if="loading" class="search-clear" icon="spinner" spin />
        <font-awesome-icon
            v-else
            v-b-tooltip.hover
            :title="titleClearSearch"
            class="search-clear"
            icon="times-circle"
            @click="setQuery()" />
    </div>
</template>
<script>
import _l from "utils/localization";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";

library.add(faSpinner);
library.add(faTimesCircle);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        query: {
            type: String,
        },
        loading: {
            type: Boolean,
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
            titleClearSearch: _l("clear search (esc)"),
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
                this.$emit("onChange", this.queryCurrent);
            }
        },
    },
};
</script>
