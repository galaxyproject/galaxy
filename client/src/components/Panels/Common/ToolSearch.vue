<template>
    <div>
        <DelayedInput
            :class="!showAdvanced && 'mb-3'"
            :query="query"
            :loading="loading"
            :show-advanced="showAdvanced"
            include-adv-btn
            :placeholder="placeholder"
            @change="checkQuery"
            @onToggle="onToggle" />
        <div
            v-if="showAdvanced"
            class="mt-2"
            description="advanced tool filters"
            @keyup.enter="onSearch"
            @keyup.esc="onToggle(false)">
            <small>Filter by tool name:</small>
            <b-form-input v-model="filterSettings['name']" size="sm" placeholder="any tool name" />
            <small class="mt-1">Filter by section:</small>
            <b-form-input v-model="filterSettings['panelSectionName']" size="sm" placeholder="any section" />
            <small class="mt-1">Filter by id:</small>
            <b-form-input v-model="filterSettings['id']" size="sm" placeholder="any id" />
            <small class="mt-1">Filter by description:</small>
            <b-form-input v-model="filterSettings['description']" size="sm" placeholder="any description" />
            <div class="mt-3">
                <b-button class="mr-1" size="sm" variant="primary" @click="onSearch">
                    <icon icon="search" />
                    <span>{{ "Search" | localize }}</span>
                </b-button>
                <b-button size="sm" description="clear filters" @click="filterSettings = {}">
                    <icon icon="redo" />
                    <span>{{ "Clear" | localize }}</span>
                </b-button>
            </div>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import DelayedInput from "components/Common/DelayedInput";

export default {
    name: "ToolSearch",
    components: {
        DelayedInput,
    },
    props: {
        currentPanelView: {
            type: String,
            required: true,
        },
        placeholder: {
            type: String,
            default: "search tools",
        },
        query: {
            type: String,
            default: null,
        },
        showAdvanced: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            favorites: ["#favs", "#favorites", "#favourites"],
            minQueryLength: 3,
            loading: false,
            filterSettings: {},
        };
    },
    computed: {
        favoritesResults() {
            const Galaxy = getGalaxyInstance();
            return Galaxy.user.getFavorites().tools;
        },
    },
    methods: {
        checkQuery(q) {
            this.$emit("onQuery", q);
            if (q && q.length >= this.minQueryLength) {
                if (this.favorites.includes(q)) {
                    this.$emit("onResults", this.favoritesResults);
                } else {
                    this.loading = true;
                    axios
                        .get(`${getAppRoot()}api/tools`, {
                            params: { q, view: this.currentPanelView },
                        })
                        .then((response) => {
                            this.loading = false;
                            this.$emit("onResults", response.data);
                        })
                        .catch((err) => {
                            this.loading = false;
                            this.$emit("onError", err);
                        });
                }
            } else {
                this.$emit("onResults", null);
            }
        },
        onSearch() {
            for (const [filter, value] of Object.entries(this.filterSettings)) {
                if (!value) {
                    delete this.filterSettings[filter];
                }
            }
            this.$router.push({ path: "/tools/advanced_search", query: this.filterSettings });
        },
        onToggle(toggleAdvanced) {
            this.$emit("update:show-advanced", toggleAdvanced);
        },
    },
};
</script>
