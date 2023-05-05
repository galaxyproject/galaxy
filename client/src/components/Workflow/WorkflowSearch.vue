<template>
    <div>
        <small v-if="showAdvanced">Filter by name:</small>
        <DelayedInput
            :class="!showAdvanced && 'mb-3'"
            :query="query"
            :delay="100"
            :loading="loading"
            :show-advanced="showAdvanced"
            :enable-advanced="enableAdvanced"
            :placeholder="showAdvanced ? 'any name' : placeholder"
            @change="checkQuery"
            @onToggle="onToggle" />
        <div
            v-if="showAdvanced"
            description="advanced workflow filters"
            @keyup.enter="onSearch"
            @keyup.esc="onToggle(false)">
            <small class="mt-1">Filter by tag:</small>
            <b-form-input v-model="filterSettings['tag']" size="sm" placeholder="any tag" />
            <small>Published:</small>
            <b-form-group class="m-0">
                <b-form-radio-group
                    v-model="filterSettings.published"
                    :options="options"
                    size="sm"
                    buttons
                    description="filter published" />
            </b-form-group>
            <small>Shared:</small>
            <b-form-group class="m-0">
                <b-form-radio-group
                    v-model="filterSettings.shared"
                    :options="options"
                    size="sm"
                    buttons
                    description="filter shared" />
            </b-form-group>
            <small>Deleted:</small>
            <b-form-group class="m-0">
                <b-form-radio-group
                    v-model="filterSettings.deleted"
                    :options="options"
                    size="sm"
                    buttons
                    description="filter deleted" />
            </b-form-group>
            <div class="mt-3">
                <b-button class="mr-1" size="sm" variant="primary" @click="onSearch">
                    <icon icon="search" />
                    <span>{{ "Search" | localize }}</span>
                </b-button>
                <b-button size="sm" @click="onToggle(false)">
                    <icon icon="redo" />
                    <span>{{ "Cancel" | localize }}</span>
                </b-button>
            </div>
        </div>
    </div>
</template>

<script>
import DelayedInput from "components/Common/DelayedInput";
import _l from "utils/localization";
import { createWorkflowQuery } from "components/Panels/utilities";

export default {
    name: "WorkflowSearch",
    components: {
        DelayedInput,
    },
    props: {
        loading: {
            type: Boolean,
            default: false,
        },
        enableAdvanced: {
            type: Boolean,
            default: false,
        },
        placeholder: {
            type: String,
            default: _l("search workflows"),
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
            filterSettings: {
                published: false,
                shared: false,
                deleted: false,
            },
            options: [
                { text: "Yes", value: true },
                { text: "No", value: false },
            ],
        };
    },
    methods: {
        checkQuery(q) {
            this.filterSettings["name"] = q;
            if (this.favorites.includes(q)) {
                this.$emit("onQuery", "#favorites");
            } else {
                this.$emit("onQuery", q);
            }
        },
        onToggle(toggleAdvanced) {
            this.$emit("update:show-advanced", toggleAdvanced);
        },
        onSearch() {
            const query = createWorkflowQuery(this.filterSettings);
            const path = "/workflows/list";
            const routerParams = query ? { path, query: { query } } : { path };
            this.$router.push(routerParams);
        },
    },
};
</script>
