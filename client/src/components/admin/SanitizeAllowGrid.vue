<template>
    <base-grid :is-loaded="isLoaded" :columns="columns" id="sanitize-allow-grid">
        <template v-slot:title> Tool Sanitization Allowlist </template>
        <template v-slot:rows>
            <template v-for="(row, index) in rows">
                <tr :key="row.tool_id" :class="[index % 2 === 0 ? 'tr' : 'odd_row']">
                    <td>{{ row.tool_name }}</td>
                    <td v-if="row.allowed">
                        <template v-if="row.toolshed">
                            <template v-for="(part, index) in row.tool_id"><span>{{ part }}</span>/</template>
                        </template>
                        <template v-else>
                            <span>{{ row.tool_id }}</span>
                        </template>
                    </td>
                    <td v-else>
                        <template v-if="row.toolshed">
                            <span>{{ row.tool_id[0] }}</span>/<span>{{ row.tool_id[1] }}</span>/<a :data-tool-id="{{ row.tool_id.slice(0, 3).join('/') }}" @click="allowHTML">{{ row.tool_id[2] }}</a>/<a :data-tool-id="{{ row.tool_id.slice(0, 4).join('/') }}" @click="allowHTML">{{ row.tool_id[3] }}</a>/<a :data-tool-id="{{ row.tool_id.slice(0, 5).join('/') }}" @click="allowHTML">{{ row.tool_id[4] }}</a>/<a :data-tool-id="{{ row.tool_id.join('/') }}"  @click="allowHTML">{{ row.tool_id[5] }}</a>
                        </template>
                        <template v-else>
                            <span>{{ row.tool_id }}</span>
                        </template>
                    </td>
                    <td v-if="row.allowed">
                        <button :data-tool-id="{{ row.tool_id.join('/') }}" @click="sanitizeHTML">Sanitize HTML</button>
                    </td>
                    <td v-else>
                        <template v-if="row.toolshed">
                            <button :data-tool-id="{{ row.tool_id  }}" @click="allowHTML">Allow HTML</button>
                        </template>
                    </td>
                </tr>
            </template>
        </template>
    </base-grid>
</template>

<script>
import BaseGrid from "./BaseGrid.vue";

export default {
    props: {
        isLoaded: {
            type: Boolean,
            required: true,
        },
        rows: {
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

};
</script>
