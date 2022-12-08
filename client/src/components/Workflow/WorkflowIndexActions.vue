<template>
    <span>
        <b-button id="workflow-create" class="m-1" @click="navigateToCreate">
            <font-awesome-icon icon="plus" />
            {{ "Create" | localize }}
        </b-button>
        <b-button id="workflow-import" class="m-1" @click="navigateToImport">
            <font-awesome-icon icon="upload" />
            {{ "Import" | localize }}
        </b-button>
    </span>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

import { faPlus, faUpload } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
library.add(faPlus, faUpload);

export default {
    components: {
        BButton,
        FontAwesomeIcon,
    },
    methods: {
        navigateToCreate: function () {
            this.$router.push("/workflows/create");
        },
        navigateToImport: function () {
            this.$router.push("/workflows/import");
        },
    },
};
</script>
