<template>
    <table class="tabletip">
        <thead>
            <tr>
                <th :colspan="dataManagerColumns.length" style="font-size: 120%">
                    Data Manager: {{ dataManagerTableName }}
                    <a
                        class="icon-btn"
                        href="javascript:void(0)"
                        :title="`Reload ${dataManagerTableName} tool data table`"
                        @click="handleReloadButtonClick"
                        ><FontAwesomeIcon icon="fa-sync"></FontAwesomeIcon
                    ></a>
                </th>
            </tr>
            <tr>
                <!-- eslint-disable-next-line vue/require-v-for-key -->
                <th v-for="column in dataManagerColumns">{{ column }}</th>
            </tr>
        </thead>
        <tbody v-for="item in dataManagerItems" :key="item.value">
            <tr>
                <!-- eslint-disable-next-line vue/require-v-for-key -->
                <td v-for="column in dataManagerColumns">{{ item[column] }}</td>
            </tr>
        </tbody>
    </table>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSync } from "@fortawesome/free-solid-svg-icons";

library.add(faSync);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        dataManagerTableName: {
            type: String,
            required: true,
        },
        dataManagerColumns: {
            type: Array,
            required: true,
        },
        dataManagerItems: {
            type: Array,
            required: true,
        },
    },
    methods: {
        handleReloadButtonClick(event) {
            this.$emit("reloaddatamanager", this.dataManagerTableName);
        },
    },
};
</script>
