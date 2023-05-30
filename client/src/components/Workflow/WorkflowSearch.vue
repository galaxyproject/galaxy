<script setup lang="ts">
import { ref, type Ref } from "vue";
import { useRouter } from "vue-router/composables";
import _l from "@/utils/localization";
import { createWorkflowQuery } from "@/components/Panels/utilities";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faAngleDoubleUp, faAngleDoubleDown } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";

const router = useRouter();

type FilterSettings = {
    name?: string;
    tag?: string;
    published?: boolean;
    shared_with_me?: boolean;
    deleted?: boolean;
};

// @ts-ignore bad library types
library.add(faAngleDoubleUp, faAngleDoubleDown);

const options = [
    { text: "Yes", value: true },
    { text: "No", value: false },
];

const filterSettings: Ref<FilterSettings> = ref({
    published: false,
    shared_with_me: false,
    deleted: false,
});

const showAdvanced = ref(true);

function onSearch() {
    const query = createWorkflowQuery(filterSettings.value);
    const path = "/workflows/list";
    const routerParams = query ? { path, query: { query } } : { path };
    router.push(routerParams);
}
</script>
<template>
    <div>
        <b-button
            class="upload-button"
            size="sm"
            :pressed="showAdvanced"
            :variant="showAdvanced ? 'info' : 'secondary'"
            @click="showAdvanced = !showAdvanced">
            <FontAwesomeIcon v-if="!showAdvanced" icon="angle-double-down" />
            <FontAwesomeIcon v-else icon="angle-double-up" />
            Search for Workflows
        </b-button>
        <div
            v-if="showAdvanced"
            description="advanced workflow filters"
            @keyup.enter="onSearch"
            @keyup.esc="showAdvanced = false">
            <small class="mt-1">Filter by name:</small>
            <b-form-input v-model="filterSettings.name" size="sm" placeholder="any name" />
            <small class="mt-1">Filter by tag:</small>
            <b-form-input v-model="filterSettings.tag" size="sm" placeholder="any tag" />
            <small>Published:</small>
            <b-form-group class="m-0">
                <b-form-radio-group
                    v-model="filterSettings.published"
                    :options="options"
                    size="sm"
                    buttons
                    description="filter published" />
            </b-form-group>
            <small>Shared:</small>
            <b-form-group class="m-0">
                <b-form-radio-group
                    v-model="filterSettings.shared_with_me"
                    :options="options"
                    size="sm"
                    buttons
                    description="filter shared" />
            </b-form-group>
            <small>Deleted:</small>
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
                <b-button size="sm" @click="showAdvanced = false">
                    <icon icon="redo" />
                    <span>{{ _l("Cancel") }}</span>
                </b-button>
            </div>
        </div>
    </div>
</template>
