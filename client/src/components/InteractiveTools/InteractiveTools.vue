<template>
    <div>
        <b-alert v-for="(message, index) in messages" :key="index" :show="3" variant="danger">{{ message }}</b-alert>
        <h2>Active Interactive Tools</h2>
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
                    :index="row.index"
                    :href="row.item.target"
                    target="_blank"
                    :name="row.item.name"
                    >{{ row.item.name }}</a
                >
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

export default {
    components: {
        UtcDate,
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
            activeInteractiveTools: [],
        };
    },
    computed: {
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
        load() {
            this.filter = "";
            this.services
                .getActiveInteractiveTools()
                .then((activeInteractiveTools) => {
                    this.activeInteractiveTools = activeInteractiveTools;
                })
                .catch((error) => {
                    this.error = error;
                });
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
                            this.activeInteractiveTools = this.activeInteractiveTools.filter((tool) => !tool.marked);
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
