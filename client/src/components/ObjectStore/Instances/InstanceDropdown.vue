<script setup lang="ts">
import "./icons";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

import type { UserConcreteObjectStore } from "./types";

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
const router = useRouter();

// TODO?
const title = "";

interface Props {
    objectStore: UserConcreteObjectStore;
}

const props = defineProps<Props>();
const routeEdit = computed(() => `/object_store_instances/${props.objectStore.id}/edit`);
const routeUpgrade = computed(() => `/object_store_instances/${props.objectStore.id}/upgrade`);
const isUpgradable = computed(() =>
    objectStoreTemplatesStore.canUpgrade(props.objectStore.template_id, props.objectStore.template_version)
);
</script>

<template>
    <div>
        <b-link
            v-b-tooltip.hover
            class="object-store-instance-dropdown font-weight-bold"
            data-toggle="dropdown"
            :title="title"
            aria-haspopup="true"
            aria-expanded="false">
            <FontAwesomeIcon icon="caret-down" />
            <span class="instance-dropdown-name">{{ props.objectStore.name }}</span>
        </b-link>
        <div class="dropdown-menu" aria-labelledby="object-store-instance-dropdown">
            <a
                v-if="isUpgradable"
                class="dropdown-item"
                @keypress="router.push(routeUpgrade)"
                @click.prevent="router.push(routeUpgrade)">
                <span class="fa fa-edit fa-fw mr-1" />
                <span v-localize>Upgrade</span>
            </a>
            <a class="dropdown-item" @keypress="router.push(routeEdit)" @click.prevent="router.push(routeEdit)">
                <span class="fa fa-edit fa-fw mr-1" />
                <span v-localize>Edit configuration</span>
            </a>
        </div>
    </div>
</template>
