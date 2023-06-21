<script setup lang="ts">
import { BButton } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";

const router = useRouter();
library.add(faPlus);

function create() {
    router.push("/pages/create");
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
