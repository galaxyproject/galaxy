<script setup lang="ts">
import { ref, type Ref } from "vue";
import { useRouter } from "vue-router/composables";
import _l from "@/utils/localization";
import { createWorkflowQuery } from "@/components/Panels/utilities";

const router = useRouter();

type FilterSettings = {
    name?: string;
    tag?: string;
    published?: boolean;
    shared_with_me?: boolean;
    deleted?: boolean;
};

const options = [
    { text: "Yes", value: true },
    { text: "No", value: false },
];

const filterSettings: Ref<FilterSettings> = ref({
    published: false,
    shared_with_me: false,
    deleted: false,
});

function onSearch() {
    const query = createWorkflowQuery(filterSettings.value);
    const path = "/workflows/list";
    const routerParams = query ? { path, query: { query } } : { path };
    router.push(routerParams);
}
</script>
<template>
    <div>
        <div description="advanced workflow filters" @keyup.enter="onSearch">
            <small class="mt-1">Filter by name:</small>
            <b-form-input v-model="filterSettings.name" size="sm" placeholder="any name" />
            <small class="mt-1">Filter by tag:</small>
            <b-form-input v-model="filterSettings.tag" size="sm" placeholder="any tag" />
            <small>Search published workflows:</small>
            <b-form-group class="m-0">
                <b-form-radio-group
                    v-model="filterSettings.published"
                    :options="options"
                    size="sm"
                    buttons
                    description="filter published" />
            </b-form-group>
            <small>Search shared workflows:</small>
            <b-form-group class="m-0">
                <b-form-radio-group
                    v-model="filterSettings.shared_with_me"
                    :options="options"
                    size="sm"
                    buttons
                    description="filter shared" />
            </b-form-group>
            <small>Search deleted workflows:</small>
            <b-form-group class="m-0">
                <b-form-radio-group
                    v-model="filterSettings.deleted"
                    :options="options"
                    size="sm"
                    buttons
                    description="filter deleted" />
            </b-form-group>
            <div class="mt-3">
                <b-button class="mr-1" size="sm" variant="primary" @click="onSearch">
                    <icon icon="search" />
                    <span>{{ _l("Search") }}</span>
                </b-button>
            </div>
        </div>
    </div>
</template>
