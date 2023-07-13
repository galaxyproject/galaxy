<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

const router = useRouter();
library.add(faPlus);

function create() {
    router.push("/pages/create");
}
</script>
<template>
    <span>
        <BButton id="page-create" class="m-1" @click="create">
            <FontAwesomeIcon icon="plus" />
            {{ "Create" | localize }}
        </BButton>
    </span>
</template>
