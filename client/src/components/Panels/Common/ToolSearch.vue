<template>
    <b-input-group class="mb-3">
        <DebouncedInput v-model="localQuery" v-slot="{ value, input }">
            <b-form-input
                size="sm"
                :value="value"
                @input="input"
                :placeholder="placeholder | localize"
                data-description="filter tool" />
        </DebouncedInput>
        <b-input-group-append>
            <b-button size="sm" @click="localQuery = ''" data-description="reset query">
                <icon icon="times" />
            </b-button>
        </b-input-group-append>
    </b-input-group>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import DebouncedInput from "components/DebouncedInput";

export default {
    name: "ToolSearch",
    components: {
        DebouncedInput,
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
        localQuery: {
            get() {
                return this.query;
            },
            set(newQuery) {
                this.checkQuery(newQuery);
            },
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
