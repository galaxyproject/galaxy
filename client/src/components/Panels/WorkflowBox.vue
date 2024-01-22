<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faGlobe, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { helpHtml, WorkflowFilters } from "@/components/Workflow/WorkflowFilters";
import { useUserStore } from "@/stores/userStore";
import { withPrefix } from "@/utils/redirect";

import FilterMenu from "@/components/Common/FilterMenu.vue";

const router = useRouter();

// @ts-ignore bad library types
library.add(faUpload, faGlobe);

const isAnonymous = computed(() => useUserStore().isAnonymous);

function onSearch(filters: Record<string, string | boolean>, filterText?: string, query?: string) {
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
                            @click="$router.push('/workflows/edit')">
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
                    <div v-html="helpHtml"></div>
                </template>
            </FilterMenu>
        </div>
    </div>
</template>
