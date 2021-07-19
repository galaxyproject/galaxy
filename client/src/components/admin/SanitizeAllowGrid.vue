<template>
    <base-grid :is-loaded="isLoaded" :columns="columns" id="sanitize-allow-grid">
        <template v-slot:title> Tool HTML Allowlist </template>
        <template v-slot:allow>
            <template v-for="(row, index) in allow">
                <tr :key="row.tool_id" :class="[index % 2 === 0 ? 'tr' : 'odd_row']">
                    <td>{{ row.tool_name }}</td>
                    <td>
                        <template v-if="row.toolshed">
                            <template v-for="(part, index) in row.tool_id">
                                <span>{{ part }}</span>
                                <strong>/</strong>
                            </template>
                        </template>
                        <template v-else>
                            <span>{{ row.tool_id[0] }}</span>
                        </template>
                    </td>
                    <td>
                        <button @click="sanitizeHTML(row.ids.allowed)">Sanitize HTML</button>
                    </td>
                </tr>
            </template>
        </template>
        <template v-slot:title> Tool HTML Blocklist </template>
        <template v-slot:sanitize>
            <template v-for="(row, index) in sanitize">
                <tr :key="row.tool_id" :class="[index % 2 === 0 ? 'tr' : 'odd_row']">
                    <td>
                        <template v-if="row.toolshed">
                            <span>{{ row.tool_id[0] }}</span>
                            <strong>/</strong>
                            <span>{{ row.tool_id[1] }}</span>
                            <strong>/</strong>
                            <a @click="allowHTML(row.ids.owner)">{{ row.tool_id[2] }}</a>
                            <strong>/</strong>
                            <a @click="allowHTML(row.ids.repository)">{{ row.tool_id[3] }}</a>
                            <strong>/</strong>
                            <a @click="allowHTML(row.ids.tool)">{{ row.tool_id[4] }}</a>
                            <strong>/</strong>
                            <a @click="allowHTML(row.ids.full)">{{ row.tool_id[5] }}</a>
                        </template>
                        <template v-else>
                            <span>{{ row.tool_id[0] }}</span>
                        </template>
                    </td>
                    <td>
                        <template v-if="!row.toolshed">
                            <button @click="allowHTML(row.ids.full)">Allow HTML</button>
                        </template>
                    </td>
                </tr>
            </template>
        </template>
    </base-grid>
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
        sanitize: {
            type: Array,
            required: true,
        },
        allow: {
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
                    this.allowList = response.data.data.allowList;
                    this.blockList = response.data.data.blockList;
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
                    this.allowList = response.data.data.allowList;
                    this.blockList = response.data.data.blockList;
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
