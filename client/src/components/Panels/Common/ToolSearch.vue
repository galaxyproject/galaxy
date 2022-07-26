<template>
    <DelayedInput class="mb-3" :query="query" :loading="loading" :placeholder="placeholder" @change="checkQuery" />
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
    },
    data() {
        return {
            favorites: ["#favs", "#favorites", "#favourites"],
            minQueryLength: 3,
            loading: false,
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
    },
};
</script>
