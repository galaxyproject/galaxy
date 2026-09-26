<template>
    <div :step-label="model.step_label">
        <FormCard :title="model.fixed_title" :icon="icon" :collapsible="true" :expanded.sync="expanded">
            <template v-slot:body>
                <FormDisplay
                    v-if="hasInputs"
                    :inputs="inputs"
                    :validation-scroll-to="validationScrollTo"
                    @onChange="onChange"
                    @onValidation="onValidation"
                    @load-more="onLoadMore"
                    @search-change="onSearchChange" />
                <div v-else class="py-2">No options available.</div>
            </template>
        </FormCard>
    </div>
</template>

<script>
import { debounce } from "lodash";

import { DEFAULT_OPTIONS_PAGE_SIZE } from "@/components/Form/Elements/FormData/types";
import WorkflowIcons from "@/components/Workflow/icons";

import { searchHistoryContents } from "./services";

import FormCard from "@/components/Form/FormCard.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";

export default {
    components: {
        FormDisplay,
        FormCard,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
        validationScrollTo: {
            type: Array,
            required: true,
        },
        historyId: {
            type: String,
            default: null,
        },
    },
    data() {
        // Shallow-copy ``model.inputs`` into local state so we can mutate
        // ``options`` / ``options_meta`` (and the existing ``flavor`` /
        // ``hide_label`` flags) without touching the prop — avoiding the
        // Vue prop-mutation antipattern. Each ``localInputs[i]`` is a fresh
        // object; the nested ``options`` object reference is shared until
        // ``_fetchStepOptions`` replaces it with a new object via spread.
        return {
            expanded: this.model.expanded,
            localInputs: (this.model.inputs || []).map((input) => ({
                ...input,
                flavor: "module",
                hide_label: this._isSimpleInputType(this.model.step_type),
            })),
        };
    },
    computed: {
        icon() {
            return WorkflowIcons[this.model.step_type];
        },
        isSimpleInput() {
            return this._isSimpleInputType(this.model.step_type);
        },
        inputs() {
            return this.localInputs;
        },
        hasInputs() {
            return this.inputs.length > 0;
        },
    },
    watch: {
        validationScrollTo() {
            if (this.validationScrollTo.length > 0) {
                this.expanded = true;
            }
        },
        "model.inputs"() {
            // Re-sync local copy if the parent ever replaces the model. The
            // workflow run form doesn't currently do this mid-render, but
            // keep the contract: ``localInputs`` mirrors ``model.inputs``
            // until paginated mutations diverge from it.
            this.localInputs = (this.model.inputs || []).map((input) => ({
                ...input,
                flavor: "module",
                hide_label: this._isSimpleInputType(this.model.step_type),
            }));
        },
    },
    created() {
        // Debounce the per-keystroke options refetch so rapid typing in the
        // dropdown search box coalesces into a single backend round trip.
        this.onSearchChange = debounce(this.onSearchChange, 400);
    },
    beforeDestroy() {
        this.onSearchChange.cancel?.();
    },
    methods: {
        onChange(data) {
            this.$emit("onChange", this.model.index, data);
        },
        onValidation(validation) {
            this.$emit("onValidation", this.model.index, validation);
        },
        _isSimpleInputType(stepType) {
            return stepType.startsWith("data_input") || stepType.startsWith("data_collection_input");
        },
        _findInputByName(name) {
            return (this.localInputs || []).find((i) => i.name === name);
        },
        _shapeContentsRow(row) {
            const src = row.history_content_type === "dataset_collection" ? "hdca" : "hda";
            return {
                id: row.id,
                src,
                name: row.name,
                hid: row.hid,
                keep: false,
                tags: row.tags || [],
            };
        },
        async _fetchStepOptions(name, src, payload = {}) {
            const input = this._findInputByName(name);
            if (!input || !this.historyId) {
                return;
            }
            const type = src === "hdca" ? "dataset_collection" : "dataset";
            const extensions = input.acceptable_extensions || [];
            const limit = payload.limit || DEFAULT_OPTIONS_PAGE_SIZE;
            const offset = payload.offset || 0;
            try {
                const rows = await searchHistoryContents(this.historyId, {
                    extensions,
                    type,
                    tag: input.tag,
                    // ``data_collection`` parameters offer hidden collections too.
                    visibleOnly: input.type !== "data_collection",
                    search: payload.search,
                    offset,
                    limit,
                });
                const shaped = (rows || []).map(this._shapeContentsRow);
                const base = (input.options && input.options[src]) || [];
                const seen = new Set(base.map((item) => `${item.id}_${item.src}`));
                const merged = base.concat(
                    shaped.filter((item) => {
                        const key = `${item.id}_${item.src}`;
                        if (seen.has(key)) {
                            return false;
                        }
                        seen.add(key);
                        return true;
                    }),
                );
                input.options = { ...(input.options || {}), [src]: merged };
                input.options_meta = {
                    ...(input.options_meta || {}),
                    [src]: { offset, limit, has_more: shaped.length === limit },
                };
                // FormDisplay renders from an internal clone and only syncs
                // server-owned attributes when the inputs prop changes by
                // identity. Bump the array reference so the fetched options
                // reach that clone without replacing its client-owned value.
                this.localInputs = [...this.localInputs];
            } catch (e) {
                console.warn("history-contents pagination failed", e);
            }
        },
        onLoadMore({ name, src, offset, limit, search }) {
            this._fetchStepOptions(name, src, { offset, limit, search });
        },
        onSearchChange({ name, src, query, limit }) {
            this._fetchStepOptions(name, src, { offset: 0, limit: limit || DEFAULT_OPTIONS_PAGE_SIZE, search: query });
        },
    },
};
</script>
