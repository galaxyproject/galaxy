<script setup lang="ts">
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed } from "vue";

import localize from "@/utils/localization";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";

interface Props {
    header: string;
    message?: string;
    createRoute: string;
}

const props = defineProps<Props>();

const createUrl = props.createRoute;

const breadcrumbItems = computed(() => [{ title: "User Preferences", to: "/user" }, { title: props.header }]);
</script>

<template>
    <div>
        <div class="d-flex">
            <BreadcrumbHeading :items="breadcrumbItems" />

            <div>
                <BButton
                    :id="`create-button-${header.toLowerCase().replace(/ /g, '-')}`"
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
