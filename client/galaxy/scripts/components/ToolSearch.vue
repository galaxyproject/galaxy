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
        <span
            class="search-clear fa fa-times-circle"
            v-b-tooltip.hover
            title="clear search (esc)"
            v-if="showClear"
            @click="clear"
        ></span>
        <span class="search-loading fa fa-spinner fa-spin" v-if="showSpinner"></span>
    </div>
</template>

<script>
import { VBTooltip } from "bootstrap-vue";
import _ from "underscore";
import axios from "axios";

import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app"; // FIXME: may be we can move it to the ToolBox?
/* global ga */

export default {
    name: "ToolSearch",
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
