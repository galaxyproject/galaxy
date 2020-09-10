<template>
    <div>
        <div>
            <b>Name:</b>
            <span>{{ trsTool.name }}</span>
        </div>
        <div>
            <b>Description:</b>
            <span>{{ trsTool.description }}</span>
        </div>
        <div>
            <b>Organization</b>
            <span>{{ trsTool.organization }}</span>
        </div>
        <div>
            <b>Versions</b>
            <ul>
                <li v-for="version in trsTool.versions" :key="version.id">
                    <b-link>{{ version.name }}</b-link>
                    <b-button id="workflow-import" class="m-1" @click="importVersion(version)">
                        <font-awesome-icon icon="upload" />
                    </b-button>
                </li>
            </ul>
        </div>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUpload } from "@fortawesome/free-solid-svg-icons";

import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

library.add(faUpload);
Vue.use(BootstrapVue);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        trsTool: {
            type: Object,
        },
    },
    methods: {
        importVersion(version) {
            this.$emit("onImport", version);
        },
    },
};
</script>
