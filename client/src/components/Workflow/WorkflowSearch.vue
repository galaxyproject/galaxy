<script setup lang="ts">
import { ref, type Ref } from "vue";
import { useRouter } from "vue-router/composables";
import DelayedInput from "@/components/Common/DelayedInput.vue";
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

const emit = defineEmits<{
    (e: "onQuery", query: string): void;
    (e: "update:show-advanced", showAdvanced: boolean): void;
}>();

const props = defineProps({
    enableAdvanced: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
    placeholder: { type: String, default: _l("search workflows") },
    query: { type: String, default: null },
    showAdvanced: { type: Boolean, default: false },
});

const favorites = ["#favs", "#favorites", "#favourites"];
const options = [
    { text: "Yes", value: true },
    { text: "No", value: false },
];

const filterSettings: Ref<FilterSettings> = ref({
    published: false,
    shared: false,
    deleted: false,
});

function checkQuery(q: string) {
    filterSettings.value.name = q;
    if (favorites.includes(q)) {
        emit("onQuery", "#favorites");
    } else {
        emit("onQuery", q);
    }
}
function onToggle(toggleAdvanced: boolean) {
    emit("update:show-advanced", toggleAdvanced);
}
function onSearch() {
    const query = createWorkflowQuery(filterSettings.value);
    const path = "/workflows/list";
    const routerParams = query ? { path, query: { query } } : { path };
    router.push(routerParams);
}
</script>
<template>
    <div>
        <small v-if="props.showAdvanced">Filter by name:</small>
        <DelayedInput
            :class="!props.showAdvanced && 'mb-3'"
            :query="props.query"
            :delay="100"
            :loading="props.loading"
            :show-advanced="props.showAdvanced"
            :enable-advanced="props.enableAdvanced"
            :placeholder="props.showAdvanced ? 'any name' : props.placeholder"
            @change="checkQuery"
            @onToggle="onToggle" />
        <div
            v-if="props.showAdvanced"
            description="advanced workflow filters"
            @keyup.enter="onSearch"
            @keyup.esc="onToggle(false)">
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
                <b-button size="sm" @click="onToggle(false)">
                    <icon icon="redo" />
                    <span>{{ _l("Cancel") }}</span>
                </b-button>
            </div>
        </div>
    </div>
</template>
