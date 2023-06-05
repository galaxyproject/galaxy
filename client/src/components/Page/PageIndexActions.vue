<script setup lang="ts">
import { BButton } from "bootstrap-vue";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";

library.add(faPlus);

interface PageIndexActionsProps {
    root: string;
}

const props = defineProps<PageIndexActionsProps>();

function create() {
    window.location.assign(`${props.root}pages/create`);
}
</script>
<template>
    <span>
        <b-button id="page-create" class="m-1" @click="create">
            <font-awesome-icon icon="plus" />
            {{ "Create" | localize }}
        </b-button>
    </span>
</template>
