<template>
    <div>
        <small v-if="showAdvanced">Filter by name:</small>
        <DelayedInput
            :class="!showAdvanced && 'mb-3'"
            :query="query"
            :show-advanced="showAdvanced"
            :enable-advanced="enableAdvanced"
            :placeholder="showAdvanced ? 'any name' : placeholder"
            @change="checkQuery"
            @onToggle="onToggle" />
        <div
            v-if="showAdvanced"
            description="advanced tool filters"
            @keyup.enter="onSearch"
            @keyup.esc="onToggle(false)">
            <small class="mt-1">Filter by section:</small>
            <b-form-input v-model="filterSettings['section']" size="sm" placeholder="any section" />
            <small class="mt-1">Filter by id:</small>
            <b-form-input v-model="filterSettings['id']" size="sm" placeholder="any id" />
            <small class="mt-1">Filter by help text:</small>
            <b-form-input v-model="filterSettings['help']" size="sm" placeholder="any help text" />
            <div class="mt-3">
                <b-button class="mr-1" size="sm" variant="primary" @click="onSearch">
                    <icon icon="search" />
                    <span>{{ "Search" | localize }}</span>
                </b-button>
                <b-button size="sm" description="clear filters" @click="onToggle(false)">
                    <icon icon="redo" />
                    <span>{{ "Cancel" | localize }}</span>
                </b-button>
            </div>
        </div>
    </div>
</template>

<script>
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
        enableAdvanced: {
            type: Boolean,
            default: false,
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
        toolbox: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            favorites: ["#favs", "#favorites", "#favourites"],
            minQueryLength: 3,
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
            this.filterSettings["name"] = q;
            this.$emit("onQuery", q);
            if (q && q.length >= this.minQueryLength) {
                if (this.favorites.includes(q)) {
                    this.$emit("onResults", this.favoritesResults);
                } else {
                    const returnedTools = [];
                    const keys = ["name", "description"];
                    for (const section of this.toolbox) {
                        if (section.elems) {
                            for (const tool of section.elems) {
                                for (const key of keys) {
                                    const actualValue = tool[key];
                                    if (actualValue && actualValue.toUpperCase().match(q.toUpperCase())) {
                                        returnedTools.push({ id: tool.id, key: key });
                                        break;
                                    }
                                }
                            }
                        }
                    }
                    // sorting results by 'key:name' before 'key:description'
                    const sortedTools = (returnedTools.sort((a, b) => b.key < a.key ? -1 : 1)).map(a => a.id);
                    this.$emit("onResults", sortedTools);
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
            this.$router.push({ path: "/tools/list", query: this.filterSettings });
        },
        onToggle(toggleAdvanced) {
            this.$emit("update:show-advanced", toggleAdvanced);
        },
    },
};
</script>
