<template>
    <b-tabs>
        <b-tab title="Toolshed Tools">
            <b-tabs>
                <b-tab title="HTML Sanitized">
                    <base-grid :is-loaded="isLoaded" :columns="toolshedColumns" id="sanitize-allow-grid">
                        <template v-slot:rows>
                            <template v-for="(row, index) in toolshedBlocked">
                                <tr :key="row.tool_id" :class="[index % 2 === 0 ? 'tr' : 'odd_row']">
                                    <td>{{ row.tool_name }}</td>
                                    <td>
                                        <span>{{ row.tool_id[0] }}</span>
                                    </td>
                                    <td>
                                        <button @click="allowHTML(row.ids.owner)">{{ row.tool_id[2] }}</button>
                                    </td>
                                    <td>
                                        <button @click="allowHTML(row.ids.repository)">{{ row.tool_id[3] }}</button>
                                    </td>
                                    <td>
                                        <button @click="allowHTML(row.ids.tool)">{{ row.tool_id[4] }}</button>
                                    </td>
                                    <td>
                                        <button @click="allowHTML(row.ids.full)">{{ row.tool_id[5] }}</button>
                                    </td>
                                </tr>
                            </template>
                        </template>
                    </base-grid>
                </b-tab>
                <b-tab title="HTML Rendered">
                    <base-grid :is-loaded="isLoaded" :columns="columns" id="sanitize-allow-grid">
                        <template v-slot:rows>
                            <template v-for="(row, index) in toolshedAllowed">
                                <tr :key="row.tool_id" :class="[index % 2 === 0 ? 'tr' : 'odd_row']">
                                    <td>{{ row.tool_name }}</td>
                                    <td>
                                        <template v-for="(part, index) in row.tool_id">
                                            <span>{{ part }}</span>
                                            <strong>/</strong>
                                        </template>
                                    </td>
                                    <td>
                                        <button @click="sanitizeHTML(row.ids.allowed)">Sanitize HTML</button>
                                    </td>
                                </tr>
                            </template>
                        </template>
                    </base-grid>
                </b-tab>
            </b-tabs>
        </b-tab>
        <b-tab title="Local Tools">
            <b-tabs>
                <b-tab title="HTML Sanitized">
                    <base-grid :is-loaded="isLoaded" :columns="columns" id="sanitize-allow-grid">
                        <template v-slot:rows>
                            <template v-for="(row, index) in localBlocked">
                                <tr :key="row.tool_id" :class="[index % 2 === 0 ? 'tr' : 'odd_row']">
                                    <td>{{ row.tool_name }}</td>
                                    <td>{{ row.tool_id[0] }}</td>
                                    <td>
                                        <button @click="allowHTML(row.ids.full)">Render HTML</button>
                                    </td>
                                </tr>
                            </template>
                        </template>
                    </base-grid>
                </b-tab>
                <b-tab title="HTML Rendered">
                    <base-grid :is-loaded="isLoaded" :columns="columns" id="sanitize-allow-grid">
                        <template v-slot:rows>
                            <template v-for="(row, index) in localAllowed">
                                <tr :key="row.tool_id" :class="[index % 2 === 0 ? 'tr' : 'odd_row']">
                                    <td>{{ row.tool_name }}</td>
                                    <td>{{ row.tool_id[0] }}</td>
                                    <td>
                                        <button @click="sanitizeHTML(row.ids.allowed)">Sanitize HTML</button>
                                    </td>
                                </tr>
                            </template>
                        </template>
                    </base-grid>
                </b-tab>
            </b-tabs>
        </b-tab>
    </b-tabs>
</template>

<script>
import BaseGrid from "./BaseGrid.vue";
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

export default {
    props: {
        isLoaded: {
            type: Boolean,
            required: true,
        },
        localAllowed: {
            type: Array,
            required: true,
        },
        localBlocked: {
            type: Array,
            required: true,
        },
        toolshedAllowed: {
            type: Array,
            required: true,
        },
        toolshedBlocked: {
            type: Array,
            required: true,
        },
    },

    data() {
        return {
            columns: [
                { text: "Tool Name", dataIndex: "tool_name" },
                { text: "Tool ID", dataIndex: "tool_id" },
                { text: "Action", dataIndex: "action" },
            ],
            toolshedColumns: [
                { text: "Tool Name", dataIndex: "tool_name" },
                { text: "Toolshed" },
                { text: "Owner" },
                { text: "Repository" },
                { text: "Tool" },
                { text: "Version" },
            ],
        };
    },

    components: {
        "base-grid": BaseGrid,
    },

    methods: {
        allowHTML(tool_id) {
            axios
                .put(`${getAppRoot()}api/sanitize_allow?tool_id=${tool_id}`, {
                    params: {
                        tool_id: tool_id,
                    },
                })
                .then((response) => {
                    this.localAllowed = response.data.data.allowed_local;
                    this.localBlocked = response.data.data.blocked_local;
                    this.toolshedAllowed = response.data.data.allowed_toolshed;
                    this.toolshedBlocked = response.data.data.blocked_toolshed;
                    this.message = response.data.message;
                    this.status = response.data.status;
                })
                .catch((error) => {
                    console.error(error);
                });
        },
        sanitizeHTML(tool_id) {
            axios
                .delete(`${getAppRoot()}api/sanitize_allow`, {
                    params: {
                        tool_id: tool_id,
                    },
                })
                .then((response) => {
                    this.localAllowed = response.data.data.allowed_local;
                    this.localBlocked = response.data.data.blocked_local;
                    this.toolshedAllowed = response.data.data.allowed_toolshed;
                    this.toolshedBlocked = response.data.data.blocked_toolshed;
                    this.message = response.data.message;
                    this.status = response.data.status;
                })
                .catch((error) => {
                    console.error(error);
                });
        },
    },

};
</script>
