<template>
    <span>
        <BButton
            id="workflow-create"
            v-b-tooltip.hover
            aria-haspopup="true"
            :title="createTitle"
            :disabled="isAnonymous"
            class="m-1"
            @click="navigateToCreate">
            <FontAwesomeIcon icon="plus" />
            {{ "Create" | localize }}
        </BButton>
        <BButton
            id="workflow-import"
            v-b-tooltip.hover
            aria-haspopup="true"
            :title="importTitle"
            :disabled="isAnonymous"
            class="m-1"
            @click="navigateToImport">
            <FontAwesomeIcon icon="upload" />
            {{ "Import" | localize }}
        </BButton>
    </span>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { mapState } from "pinia";

import { useUserStore } from "@/stores/userStore";

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
            this.$router.push("/workflows/edit");
        },
        navigateToImport: function () {
            this.$router.push("/workflows/import");
        },
    },
};
</script>
