<script setup lang="ts">
import "./icons";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCol, BRow } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

import _l from "@/utils/localization";

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
                    {{ _l("Create") }}
                </BButton>
            </BCol>
        </BRow>
    </div>
</template>
