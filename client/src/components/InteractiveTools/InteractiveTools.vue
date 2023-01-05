<template>
    <div aria-labelledby="interactive-tools-heading">
        <b-alert v-for="(message, index) in messages" :key="index" :show="3" variant="danger">{{ message }}</b-alert>
        <h1 id="interactive-tools-heading" class="h-lg">Active Interactive Tools</h1>
        <b-row class="mb-3">
            <b-col cols="6">
                <b-input
                    id="interactivetool-search"
                    v-model="filter"
                    class="m-1"
                    name="query"
                    placeholder="Search Interactive Tool"
                    autocomplete="off"
                    type="text" />
            </b-col>
        </b-row>
        <b-table
            id="interactive-tool-table"
            striped
            :fields="fields"
            :items="activeInteractiveTools"
            :filter="filter"
            @filtered="filtered">
            <template v-slot:cell(checkbox)="row">
                <b-form-checkbox :id="createId('checkbox', row.item.id)" v-model="row.item.marked" />
            </template>
            <template v-slot:cell(name)="row">
                <a
                    :id="createId('link', row.item.id)"
                    v-b-tooltip
                    title="Open Interactive Tool"
                    :index="row.index"
                    :href="row.item.target"
                    target="_blank"
                    :name="row.item.name"
                    >{{ row.item.name }}
                    <font-awesome-icon icon="external-link-alt" />
                </a>
            </template>
            <template v-slot:cell(job_info)="row">
                <label v-if="row.item.active"> running </label>
                <label v-else> stopped </label>
            </template>
            <template v-slot:cell(created_time)="row">
                <UtcDate :date="row.item.created_time" mode="elapsed" />
            </template>
            <template v-slot:cell(last_updated)="row">
                <UtcDate :date="row.item.modified_time" mode="elapsed" />
            </template>
        </b-table>
        <label v-if="isActiveToolsListEmpty">You do not have active interactive tools yet </label>
        <div v-if="showNotFound">
            No matching entries found for: <span class="font-weight-bold">{{ filter }}</span
            >.
        </div>
        <b-button
            v-if="isCheckboxMarked"
            id="stopInteractiveTool"
            v-b-tooltip.hover.bottom
            title="Terminate selected tools"
            @click.stop="stopInteractiveToolSession()"
            >Stop
        </b-button>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services";
import UtcDate from "components/UtcDate";
import { mapActions, mapState } from "pinia";
import { useEntryPointStore } from "../../stores/entryPointStore";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";

library.add(faExternalLinkAlt);

export default {
    components: {
        UtcDate,
        FontAwesomeIcon,
    },
    data() {
        return {
            error: null,
            fields: [
                {
                    label: "",
                    key: "checkbox",
                },
                {
                    label: "Name",
                    key: "name",
                    sortable: true,
                },
                {
                    label: "Job Info",
                    key: "job_info",
                    sortable: true,
                },
                {
                    label: "Created",
                    key: "created_time",
                    sortable: true,
                },
                {
                    label: "Last Updated",
                    key: "last_updated",
                    sortable: true,
                },
            ],
            filter: "",
            messages: [],
            nInteractiveTools: 0,
        };
    },
    computed: {
        ...mapState(useEntryPointStore, { activeInteractiveTools: "entryPoints" }),
        showNotFound() {
            return this.nInteractiveTools === 0 && this.filter && !this.isActiveToolsListEmpty;
        },
        isCheckboxMarked() {
            return this.activeInteractiveTools.some((tool) => tool.marked);
        },
        isActiveToolsListEmpty() {
            return this.activeInteractiveTools.length === 0;
        },
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.load();
    },
    methods: {
        ...mapActions(useEntryPointStore, ["ensurePollingEntryPoints", "removeEntryPoint"]),
        load() {
            this.ensurePollingEntryPoints();
            this.filter = "";
        },
        filtered: function (items) {
            this.nInteractiveTools = items.length;
        },
        stopInteractiveToolSession() {
            this.activeInteractiveTools
                .filter((tool) => tool.marked)
                .map((tool) =>
                    this.services
                        .stopInteractiveTool(tool.id)
                        .then((response) => {
                            this.removeEntryPoint(tool.id);
                        })
                        .catch((error) => {
                            this.messages.push(`Failed to stop interactive tool ${tool.name}: ${error.message}`);
                        })
                );
        },
        createId(tagLabel, id) {
            return tagLabel + "-" + id;
        },
    },
};
</script>
