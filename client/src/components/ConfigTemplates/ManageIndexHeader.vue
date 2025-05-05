<script setup lang="ts">
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";

import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";
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
        <BreadcrumbHeading :items="breadcrumbItems">
            <div>
                <GButton
                    :id="`create-button-${header.toLowerCase().replace(/ /g, '-')}`"
                    tooltip
                    title="Create new file source"
                    size="small"
                    outline
                    color="blue"
                    :to="createUrl">
                    <FontAwesomeIcon :icon="faPlus" />
                    {{ localize("Create") }}
                </GButton>
            </div>
        </BreadcrumbHeading>

        <BAlert v-if="message" show dismissible>
            {{ message || "" }}
        </BAlert>
    </div>
</template>
