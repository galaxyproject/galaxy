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

const breadcrumbItems = computed(() => [{ title: "用户偏好", to: "/user" }, { title: props.header }]);
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems">
            <div>
                <BButton
                    :id="`create-button-${header.toLowerCase().replace(/ /g, '-')}`"
                    v-b-tooltip.hover.noninteractive
                    title="创建新的文件源"
                    size="sm"
                    variant="outline-primary"
                    :to="createUrl">
                    <FontAwesomeIcon :icon="faPlus" />
                    {{ localize("创建") }}
                </BButton>
            </div>
        </BreadcrumbHeading>

        <BAlert v-if="message" show dismissible>
            {{ message || "" }}
        </BAlert>
    </div>
</template>
