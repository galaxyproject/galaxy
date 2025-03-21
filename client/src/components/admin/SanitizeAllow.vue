<template>
    <div>
        <message :message="message" :status="status"></message>
        <b-tabs>
            <b-tab title="工具仓库工具">
                <b-tabs>
                    <b-tab title="HTML 精简">
                        <base-grid id="sanitize-allow-grid" :is-loaded="isLoaded" :columns="toolshedColumns">
                            <template v-slot:rows>
                                <template v-for="(row, blockedIdx) in toolshedBlocked">
                                    <tr :key="blockedIdx">
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
                    <b-tab title="HTML 渲染">
                        <base-grid id="sanitize-allow-grid" :is-loaded="isLoaded" :columns="columns">
                            <template v-slot:rows>
                                <template v-for="(row, allowedIdx) in toolshedAllowed">
                                    <tr :key="allowedIdx">
                                        <td>
                                            <span v-if="row.tool_name">
                                                {{ row.tool_name }}
                                            </span>
                                            <span v-else>
                                                <i>未安装</i>
                                            </span>
                                        </td>
                                        <td>
                                            <template v-for="(part, part_idx) in row.tool_id">
                                                <template v-if="part_idx > 0">/</template>
                                                <span :key="part_idx">{{ part }}</span>
                                            </template>
                                        </td>
                                        <td>
                                            <button @click="sanitizeHTML(row.ids.allowed)">清理 HTML</button>
                                        </td>
                                    </tr>
                                </template>
                            </template>
                        </base-grid>
                    </b-tab>
                </b-tabs>
            </b-tab>
            <b-tab title="本地工具">
                <b-tabs>
                    <b-tab title="HTML 已清理">
                        <base-grid id="sanitize-allow-grid" :is-loaded="isLoaded" :columns="columns">
                            <template v-slot:rows>
                                <template v-for="(row, localBlockedIdx) in localBlocked">
                                    <tr :key="localBlockedIdx">
                                        <td>{{ row.tool_name }}</td>
                                        <td>{{ row.tool_id[0] }}</td>
                                        <td>
                                            <button @click="allowHTML(row.ids.full)">渲染 HTML</button>
                                        </td>
                                    </tr>
                                </template>
                            </template>
                        </base-grid>
                    </b-tab>
                    <b-tab title="HTML 渲染">
                        <base-grid id="sanitize-allow-grid" :is-loaded="isLoaded" :columns="columns">
                            <template v-slot:rows>
                                <template v-for="(row, localAllowedIdx) in localAllowed">
                                    <tr :key="localAllowedIdx">
                                        <td>
                                            <span v-if="row.tool_name">
                                                {{ row.tool_name }}
                                            </span>
                                            <span v-else>
                                                <i>未安装</i>
                                            </span>
                                        </td>
                                        <td>{{ row.tool_id[0] }}</td>
                                        <td>
                                            <button @click="sanitizeHTML(row.ids.allowed)">清理 HTML</button>
                                        </td>
                                    </tr>
                                </template>
                            </template>
                        </base-grid>
                    </b-tab>
                </b-tabs>
            </b-tab>
        </b-tabs>
    </div>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

import Message from "../Message.vue";
import BaseGrid from "./BaseGrid.vue";

export default {
    components: {
        message: Message,
        "base-grid": BaseGrid,
    },
    data() {
        return {
            isLoaded: false,
            localAllowed: [],
            localBlocked: [],
            toolshedAllowed: [],
            toolshedBlocked: [],
            columns: [
                { text: "工具名称", dataIndex: "tool_name" },
                { text: "工具 ID", dataIndex: "tool_id" },
                { text: "操作", dataIndex: "action" },
            ],
            toolshedColumns: [
                { text: "工具名称", dataIndex: "tool_name" },
                { text: "工具仓库" },
                { text: "所有者" },
                { text: "仓库" },
                { text: "工具" },
                { text: "版本" },
            ],
            message: "",
            status: "",
        };
    },

    created() {
        axios
            .get(`${getAppRoot()}api/sanitize_allow`)
            .then((response) => {
                this.isLoaded = true;
                this.localAllowed = response.data.allowed_local;
                this.localBlocked = response.data.blocked_local;
                this.toolshedAllowed = response.data.allowed_toolshed;
                this.toolshedBlocked = response.data.blocked_toolshed;
                this.message = response.data.message;
                this.status = response.data.status;
            })
            .catch((error) => {
                console.error(error);
            });
    },

    methods: {
        allowHTML(tool_id) {
            axios
                .put(`${getAppRoot()}api/sanitize_allow?tool_id=${encodeURIComponent(tool_id)}`, {
                    params: {
                        tool_id: tool_id,
                    },
                })
                .then((response) => {
                    this.localAllowed = response.data.allowed_local;
                    this.localBlocked = response.data.blocked_local;
                    this.toolshedAllowed = response.data.allowed_toolshed;
                    this.toolshedBlocked = response.data.blocked_toolshed;
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
                    this.localAllowed = response.data.allowed_local;
                    this.localBlocked = response.data.blocked_local;
                    this.toolshedAllowed = response.data.allowed_toolshed;
                    this.toolshedBlocked = response.data.blocked_toolshed;
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
