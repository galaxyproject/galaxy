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
            // Keep the array reference stable across paginated refreshes:
            // ``_fetchStepOptions`` mutates a single ``localInputs[i]``'s
            // ``options`` / ``options_meta`` properties (not the array), so
            // Vue's ``v-for`` in the child ``FormDisplay`` doesn't unmount
            // its rendered children. That matters because
            // ``select_set_value`` (used by ``test_execution_with_multiple_inputs``)
            // types into vue-multiselect's input, sleeps ``UX_RENDER``, then
            // sends Enter on the same element reference — a remount during
            // that window would invalidate it.
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
            console.log("emitting default change", data);
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
        async _fetchStepOptions(name, src, payload = {}, mode = "append") {
            const input = this._findInputByName(name);
            if (!input || !this.historyId) {
                return;
            }
            const type = src === "hdca" ? "dataset_collection" : "dataset";
            const extensions = input.acceptable_extensions || [];
            const limit = payload.limit || 50;
            const offset = payload.offset || 0;
            try {
                const rows = await searchHistoryContents(this.historyId, {
                    extensions,
                    type,
                    search: payload.search,
                    offset,
                    limit,
                });
                const shaped = (rows || []).map(this._shapeContentsRow);
                let merged;
                if (mode === "replace") {
                    merged = shaped;
                } else {
                    const base = (input.options && input.options[src]) || [];
                    const seen = new Set();
                    merged = [...base, ...shaped].filter((item) => {
                        const k = `${item.id}_${item.src}`;
                        if (seen.has(k)) {
                            return false;
                        }
                        seen.add(k);
                        return true;
                    });
                }
                // Mutate the local copy in place; ``localInputs`` is
                // component-owned (declared in ``data()``), so this is not
                // prop mutation. The ``localInputs`` array reference stays
                // stable across paginated refreshes — Vue's ``v-for`` in the
                // child ``FormDisplay`` doesn't unmount its children, so
                // vue-multiselect's ``<input>`` survives across the
                // search-change debounce.
                input.options = { ...(input.options || {}), [src]: merged };
                input.options_meta = {
                    ...(input.options_meta || {}),
                    [src]: { offset, limit, has_more: shaped.length === limit },
                };
            } catch (e) {
                console.warn("history-contents pagination failed", e);
            }
        },
        onLoadMore({ name, src, offset, limit, search }) {
            this._fetchStepOptions(name, src, { offset, limit, search }, "append");
        },
        onSearchChange({ name, src, query, limit }) {
            this._fetchStepOptions(name, src, { offset: 0, limit: limit || 50, search: query }, "replace");
        },
    },
};
</script>
