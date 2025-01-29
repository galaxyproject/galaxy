<script setup lang="ts">
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";

import localize from "@/utils/localization";

import Heading from "@/components/Common/Heading.vue";

interface Props {
    message?: string;
    createButtonId: string;
    createRoute: string;
}

const props = defineProps<Props>();

const createUrl = props.createRoute;
</script>

<template>
    <div>
        <div class="d-flex">
            <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">Remote File Sources</Heading>

            <div>
                <BButton
                    :id="createButtonId"
                    v-b-tooltip.hover.noninteractive
                    title="Create new file source"
                    size="sm"
                    variant="outline-primary"
                    :to="createUrl">
                    <FontAwesomeIcon :icon="faPlus" />
                    {{ localize("Create") }}
                </BButton>
            </div>
        </div>

        <BAlert v-if="message" show dismissible>
            {{ message || "" }}
        </BAlert>
    </div>
</template>
