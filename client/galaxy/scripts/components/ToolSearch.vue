<template>
    <div class="search-input">
        <input
            v-model="query"
            ref="input"
            @click="focusAndSelect"
            @keydown.esc="clear"
            class="search-query parent-width tool-search-query"
            name="query"
            placeholder="search tools"
            autocomplete="off"
            type="text"
        />
        <font-awesome-icon
            class="search-clear"
            v-if="showClear"
            icon="times-circle"
            v-b-tooltip.hover
            title="clear search (esc)"
            @click="clear"
        />
        <font-awesome-icon class="search-loading" v-if="showSpinner" icon="spinner" spin />
    </div>
</template>

<script>
import { VBTooltip } from "bootstrap-vue";
import _ from "underscore";
import axios from "axios";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";

import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app"; // FIXME: may be we can move it to the ToolBox?
/* global ga */

library.add(faSpinner);
library.add(faTimesCircle);

export default {
    name: "ToolSearch",
    components: {
        FontAwesomeIcon
    },
    directives: {
        "v-b-tooltip": VBTooltip
    },
    data() {
        return {
            "api/tools": `${getAppRoot()}api/tools`, // FIXME: 'api/tools' and naming conventions?
            query: "",
            previousQuery: "",
            reservedKeywordsSynonyms: {
                favourites: ["#favs", "#favorites", "#favourites"]
            },
            minQueryLength: 3,

            showSpinner: false,
            showClear: true
        };
    },
    watch: {
        query(newVal) {
            this.checkQuery(newVal);
        }
    },
    methods: {
        checkQuery: _.debounce(function(q) {
            const Galaxy = getGalaxyInstance();

            if (q !== this.previousQuery) {
                this.previousQuery = q;

                if (q.length >= this.minQueryLength) {
                    if (this.reservedKeywordsSynonyms["favourites"].includes(q)) {
                        this.$emit("results", Galaxy.user.getFavorites().tools);
                    } else {
                        this.showSpinner = true;
                        this.showClear = false;

                        // log the search to analytics if present
                        if (typeof ga !== "undefined") {
                            ga("send", "pageview", `${getAppRoot()}?q=${q}`);
                        }

                        axios
                            .get(this["api/tools"], {
                                params: { q }
                            })
                            .then(this.handleResponse)
                            .catch(this.handleError);
                    }
                } else {
                    this.$emit("results", null);
                }
            }
        }, 400),
        handleResponse(response) {
            this.$emit("results", response.data);

            // console.log(data);
            setTimeout(() => {
                this.showSpinner = false;
                this.showClear = true;
            }, 200);
        },
        handleError(err) {
            // FIXME: if in debug mode
            console.warn(err);
        },
        clear() {
            this.$emit("results", null);
            this.query = "";
            this.focusAndSelect();
        },
        focusAndSelect() {
            this.$refs["input"].focus();
            this.$refs["input"].select();
        }
    }
};
</script>

<style scoped>
.search-loading {
    /* needed to override default styles */
    display: block;
}
</style>
