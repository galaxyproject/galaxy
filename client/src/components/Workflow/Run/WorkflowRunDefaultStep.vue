<template>
    <div :step-label="model.step_label">
        <FormCard :title="model.fixed_title" :icon="icon" :collapsible="true" :expanded.sync="expanded">
            <template v-slot:title>
                <span v-if="credentialInfo?.toolId" v-g-tooltip.hover title="Uses credentials">
                    <FontAwesomeIcon :icon="faKey" fixed-width />
                </span>
            </template>
            <template v-slot:body>
                <ToolCredentials
                    v-if="credentialInfo?.toolId"
                    :tool-id="credentialInfo.toolId"
                    :tool-version="credentialInfo.toolVersion" />
                <FormMessage :message="errorText" variant="danger" :persistent="true" />
                <FormDisplay
                    :inputs="modelInputs"
                    :sustain-repeats="true"
                    :sustain-conditionals="true"
                    :replace-params="replaceParams"
                    :validation-scroll-to="validationScrollTo"
                    collapsed-enable-text="Edit"
                    :collapsed-enable-icon="faEdit"
                    collapsed-disable-text="Undo"
                    :collapsed-disable-icon="faUndo"
                    @load-more="onLoadMore"
                    @search-change="onSearchChange"
                    @onChange="onChange"
                    @onValidation="onValidation" />
            </template>
        </FormCard>
    </div>
</template>

<script>
import { faEdit, faKey, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { debounce } from "lodash";
import { mapState } from "pinia";

import { findInputByDottedName, visitInputs } from "@/components/Form/utilities";
import WorkflowIcons from "@/components/Workflow/icons";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";

import { getTool } from "./services";

import FormCard from "@/components/Form/FormCard.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import FormMessage from "@/components/Form/FormMessage.vue";
import ToolCredentials from "@/components/Tool/ToolCredentials.vue";

export default {
    components: {
        FontAwesomeIcon,
        ToolCredentials,
        FormDisplay,
        FormCard,
        FormMessage,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
        replaceParams: {
            type: Object,
            default: null,
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
        return {
            faEdit,
            faKey,
            faUndo,
            expanded: this.model.expanded,
            errorText: null,
            modelData: {},
            modelIndex: {},
            modelInputs: this.model.inputs,
        };
    },
    computed: {
        ...mapState(useHistoryItemsStore, ["lastUpdateTime"]),
        credentialInfo() {
            if (!this.model.credentials?.length) {
                return null;
            }

            return {
                toolId: this.model.id,
                toolVersion: this.model.version,
                toolCredentials: this.model.credentials,
            };
        },
        icon() {
            return WorkflowIcons[this.model.step_type];
        },
        historyStatusKey() {
            return `${this.historyId}_${this.lastUpdateTime}`;
        },
    },
    watch: {
        validationScrollTo() {
            if (this.validationScrollTo.length > 0) {
                this.expanded = true;
            }
        },
        historyStatusKey() {
            this.onHistoryChange();
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
        onCreateIndex() {
            this.modelIndex = {};
            visitInputs(this.modelInputs, (input, name) => {
                this.modelIndex[name] = input;
            });
        },
        onHistoryChange() {
            this.onUpdate();
        },
        onChange(data, refreshRequest) {
            this.modelData = data;
            if (refreshRequest) {
                this.onUpdate();
            }
            this.$emit("onChange", this.model.index, data);
        },
        onUpdate() {
            getTool(this.model.id, this.model.version, this.modelData, this.historyId).then(
                (newModel) => {
                    this.onCreateIndex();
                    visitInputs(newModel.inputs, (newInput, name) => {
                        const input = this.modelIndex[name];
                        input.options = newInput.options;
                        input.textable = newInput.textable;
                    });
                    this.modelInputs = JSON.parse(JSON.stringify(this.modelInputs));
                },
                (errorText) => {
                    this.errorText = errorText;
                },
            );
        },
        onValidation(validation) {
            this.$emit("onValidation", this.model.index, validation);
        },
        /**
         * Lazy-load the next page of options for a paginated data parameter
         * dropdown. Mirrors ``ToolForm.vue:onLoadMore`` but routes through
         * ``getTool`` since the workflow run form fetches per-step tool data
         * via ``Workflow/Run/services.js``. Append-merges the new options into
         * the matching parameter so already-loaded items stay visible.
         */
        onLoadMore({ name, src, offset, limit, search }) {
            const spec = { offset, limit };
            if (search) {
                spec.search = search;
            }
            const optionsPagination = { [name]: { [src]: spec } };
            getTool(this.model.id, this.model.version, this.modelData, this.historyId, optionsPagination).then(
                (newModel) => {
                    const target = findInputByDottedName(this.modelInputs, name);
                    const incoming = findInputByDottedName(newModel.inputs, name);
                    if (!target || !incoming) {
                        return;
                    }
                    const existing = (target.options && target.options[src]) || [];
                    const newOptions = (incoming.options && incoming.options[src]) || [];
                    const seen = new Set(existing.map((o) => `${o.id}_${o.src}`));
                    const appended = existing.concat(newOptions.filter((o) => !seen.has(`${o.id}_${o.src}`)));
                    target.options = { ...target.options, [src]: appended };
                    if (incoming.options_meta && incoming.options_meta[src]) {
                        target.options_meta = {
                            ...(target.options_meta || {}),
                            [src]: incoming.options_meta[src],
                        };
                    }
                    this.modelInputs = JSON.parse(JSON.stringify(this.modelInputs));
                },
                (errorText) => {
                    this.errorText = errorText;
                },
            );
        },
        /**
         * Refetch the parameter's options filtered by the typed search query
         * and **replace** (not append) the local options/meta — we want the
         * narrowed list, not a union with whatever was previously loaded.
         */
        onSearchChange({ name, src, query, limit }) {
            const spec = { offset: 0, limit };
            if (query) {
                spec.search = query;
            }
            const optionsPagination = { [name]: { [src]: spec } };
            getTool(this.model.id, this.model.version, this.modelData, this.historyId, optionsPagination).then(
                (newModel) => {
                    const target = findInputByDottedName(this.modelInputs, name);
                    const incoming = findInputByDottedName(newModel.inputs, name);
                    if (!target || !incoming) {
                        return;
                    }
                    target.options = { ...target.options, [src]: incoming.options?.[src] || [] };
                    if (incoming.options_meta && incoming.options_meta[src]) {
                        target.options_meta = {
                            ...(target.options_meta || {}),
                            [src]: incoming.options_meta[src],
                        };
                    }
                    this.modelInputs = JSON.parse(JSON.stringify(this.modelInputs));
                },
                (errorText) => {
                    this.errorText = errorText;
                },
            );
        },
    },
};
</script>
