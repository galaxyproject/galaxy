<template>
    <span>
        <b-button
            id="workflow-create"
            v-b-tooltip.hover
            aria-haspopup="true"
            :title="createTitle"
            :disabled="isAnonymous"
            class="m-1"
            @click="navigateToCreate">
            <font-awesome-icon icon="plus" />
            {{ "Create" | localize }}
        </b-button>
        <b-button
            id="workflow-import"
            v-b-tooltip.hover
            aria-haspopup="true"
            :title="importTitle"
            :disabled="isAnonymous"
            class="m-1"
            @click="navigateToImport">
            <font-awesome-icon icon="upload" />
            {{ "Import" | localize }}
        </b-button>
    </span>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";

import { faPlus, faUpload } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
library.add(faPlus, faUpload);

export default {
    components: {
        BButton,
        FontAwesomeIcon,
    },
    computed: {
        ...mapState(useUserStore, ["isAnonymous"]),
        createTitle() {
            return this.isAnonymous ? "Please log in or register to use this feature" : "Create a new workflow";
        },
        importTitle() {
            return this.isAnonymous
                ? "Please log in or register to use this feature"
                : "Import a workflow from URL or registry";
        },
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
