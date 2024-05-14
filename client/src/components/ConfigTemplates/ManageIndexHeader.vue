<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCol, BRow } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

import localize from "@/utils/localization";

library.add(faPlus);

interface Props {
    message: String | null | undefined;
    createButtonId: string;
    createRoute: string;
}

defineProps<Props>();

const router = useRouter();
</script>

<template>
    <div>
        <BAlert v-if="message" show dismissible>
            {{ message || "" }}
        </BAlert>
        <BRow class="mb-3">
            <BCol>
                <BButton :id="createButtonId" class="m-1 float-right" @click="router.push(createRoute)">
                    <FontAwesomeIcon icon="plus" />
                    {{ localize("Create") }}
                </BButton>
            </BCol>
        </BRow>
    </div>
</template>
