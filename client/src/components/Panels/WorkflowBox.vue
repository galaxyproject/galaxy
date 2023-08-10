<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faGlobe, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { useUserStore } from "@/stores/userStore";
import Filtering, { contains, type Converter, equals, toBool, type ValidFilter } from "@/utils/filtering";
import { withPrefix } from "@/utils/redirect";

import FilterMenu from "@/components/Common/FilterMenu.vue";

const router = useRouter();

// @ts-ignore bad library types
library.add(faUpload, faGlobe);

const validFilters: Record<string, ValidFilter<string | boolean>> = {
    name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
    tag: { placeholder: "tag", type: String, handler: contains("tag"), menuItem: true },
    published: {
        placeholder: "Filter on published workflows",
        type: Boolean,
        boolType: "is",
        handler: equals("published", "published", toBool as Converter<string | boolean>),
        menuItem: true,
    },
    importable: {
        placeholder: "Filter on importable workflows",
        type: Boolean,
        boolType: "is",
        handler: equals("importable", "importable", toBool as Converter<string | boolean>),
        menuItem: true,
    },
    shared_with_me: {
        placeholder: "Filter on workflows shared with me",
        type: Boolean,
        boolType: "is",
        handler: equals("shared_with_me", "shared_with_me", toBool as Converter<string | boolean>),
        menuItem: true,
    },
    deleted: {
        placeholder: "Filter on deleted workflows",
        type: Boolean,
        boolType: "is",
        handler: equals("deleted", "deleted", toBool as Converter<string | boolean>),
        menuItem: true,
    },
};

const WorkflowFilters: Filtering<string | boolean> = new Filtering(validFilters, undefined, false);

const isAnonymous = computed(() => useUserStore().isAnonymous);

function onSearch(filters: Record<string, string | boolean>, filterText?: string) {
    const query = filterText;
    const path = "/workflows/list";
    const routerParams = query ? { path, query: { query } } : { path };
    router.push(routerParams);
}

function userTitle(title: string) {
    if (isAnonymous.value == true) {
        return `Log in to ${title}`;
    } else {
        return title;
    }
}
</script>

<template>
    <div class="unified-panel" aria-labelledby="workflowbox-heading">
        <div unselectable="on">
            <div class="unified-panel-header-inner">
                <nav class="d-flex justify-content-between mx-3 my-2">
                    <h2 v-localize class="m-1 h-sm">Workflows</h2>
                    <b-button-group>
                        <b-button
                            v-b-tooltip.bottom.hover
                            data-description="create new workflow"
                            size="sm"
                            variant="link"
                            :title="userTitle('Create new workflow')"
                            :disabled="isAnonymous"
                            @click="$router.push('/workflows/create')">
                            <Icon fixed-width icon="plus" />
                        </b-button>
                        <b-button
                            v-b-tooltip.bottom.hover
                            data-description="import workflow"
                            size="sm"
                            variant="link"
                            :title="userTitle('Import workflow')"
                            :disabled="isAnonymous"
                            @click="$router.push('/workflows/import')">
                            <FontAwesomeIcon icon="upload" />
                        </b-button>
                        <b-button
                            v-b-tooltip.bottom.hover
                            data-description="published workflows"
                            size="sm"
                            variant="link"
                            title="Published workflows"
                            @click="$router.push('/workflows/list_published')">
                            <FontAwesomeIcon icon="fa-globe" />
                        </b-button>
                    </b-button-group>
                </nav>
            </div>
        </div>
        <div class="unified-panel-controls">
            <div v-if="isAnonymous">
                <b-badge class="alert-info w-100">
                    Please <a :href="withPrefix('/login')">log in or register</a> to create workflows.
                </b-badge>
            </div>
            <FilterMenu
                v-else
                name="Workflows"
                :filter-class="WorkflowFilters"
                has-help
                menu-type="standalone"
                @on-search="onSearch">
                <template v-slot:menu-help-text>
                    <div>
                        <p>This menu can be used to filter workflows in <code>workflows/list</code>.</p>

                        <p>
                            Filters entered here will be searched against workflow names and workflow tags, along with
                            the provided checkbox filters. Notice by default the search is not case-sensitive. If the
                            quoted version of tag is used, the search is case sensitive and only full matches will be
                            returned. So <code>name:'RNAseq'</code> would show only workflows named exactly
                            <code>RNAseq</code>.
                        </p>

                        <p>The available filtering tags are:</p>
                        <dl>
                            <dt><code>name</code></dt>
                            <dd>Shows workflows with the given sequence of characters in their names.</dd>
                            <dt><code>tag</code></dt>
                            <dd>
                                Shows workflows with the given workflow tag. You may also click on a tag to filter on
                                that tag directly.
                            </dd>
                            <dt><code>is:published</code></dt>
                            <dd>Shows published workflows.</dd>
                            <dt><code>is:importable</code></dt>
                            <dd>Shows importable workflows (this also means they are URL generated).</dd>
                            <dt><code>is:shared_with_me</code></dt>
                            <dd>Shows workflows shared by another user directly with you.</dd>
                            <dt><code>is:deleted</code></dt>
                            <dd>Shows deleted workflows.</dd>
                        </dl>
                    </div>
                </template>
            </FilterMenu>
        </div>
    </div>
</template>
