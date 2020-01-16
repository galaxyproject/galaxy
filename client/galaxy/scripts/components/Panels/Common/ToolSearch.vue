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
import { getGalaxyInstance } from "app";

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
            query: "",
            previousQuery: "",
            favorites: ["#favs", "#favorites", "#favourites"],
            minQueryLength: 3,
            showSpinner: false,
            showClear: true,
            responseDelay: 200,
            debounceDelay: 400
        };
    },
    watch: {
        query(newVal) {
            _.debounce(this.checkQuery, this.debounceDelay)(newVal);
        }
    },
    methods: {
        checkQuery(q) {
            const Galaxy = getGalaxyInstance();
            if (q !== this.previousQuery) {
                this.previousQuery = q;
                if (q.length >= this.minQueryLength) {
                    if (this.favorites.includes(q)) {
                        this.$emit("results", Galaxy.user.getFavorites().tools);
                    } else {
                        this.showSpinner = true;
                        this.showClear = false;
                        axios
                            .get(`${getAppRoot()}api/tools`, {
                                params: { q }
                            })
                            .then(this.handleResponse)
                            .catch(this.handleError);
                    }
                } else {
                    this.$emit("results", null);
                }
            }
        },
        handleResponse(response) {
            this.$emit("results", response.data);
            setTimeout(() => {
                this.showSpinner = false;
                this.showClear = true;
            }, this.responseDelay);
        },
        handleError(err) {
            console.warn(err);
            this.$emit("onError", err);
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
