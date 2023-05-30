<script setup lang="ts">
import { getGalaxyInstance } from "@/app";
import { withPrefix } from "@/utils/redirect";
import { computed, type ComputedRef } from "vue";
import WorkflowSearch from "@/components/Workflow/WorkflowSearch.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faUpload, faGlobe } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";

// @ts-ignore bad library types
library.add(faUpload, faGlobe);

// computed
const isUser: ComputedRef<boolean> = computed(() => {
    const Galaxy = getGalaxyInstance();
    return !!(Galaxy.user && Galaxy.user.id);
});
</script>

<template>
    <div class="unified-panel" aria-labelledby="workflowbox-heading">
        <div unselectable="on">
            <div class="unified-panel-header-inner">
                <nav class="d-flex justify-content-between mx-3 my-2">
                    <h2 id="workflowbox-heading" v-localize class="m-1 h-sm">Workflows</h2>
                    <div v-if="isUser" class="panel-header-buttons">
                        <b-button
                            v-b-tooltip.bottom.hover
                            data-description="create new workflow"
                            size="sm"
                            variant="link"
                            title="Create new workflow"
                            @click="$router.push('/workflows/create')">
                            <Icon fixed-width icon="plus" />
                        </b-button>
                    </div>
                </nav>
            </div>
        </div>
        <div class="unified-panel-controls">
            <div v-if="!isUser">
                <b-badge class="alert-info w-100">
                    Please <a :href="withPrefix('/login')">log in or register</a> to create workflows.
                </b-badge>
            </div>
            <div v-else>
                <b-button v-if="isUser" class="upload-button" size="sm" @click="$router.push('/workflows/import')">
                    <FontAwesomeIcon icon="upload" />
                    Import Workflow
                </b-button>
                <b-button class="upload-button" size="sm" @click="$router.push('/workflows/list_published')">
                    <FontAwesomeIcon icon="fa-globe" />
                    Published Workflows
                </b-button>
                <WorkflowSearch />
            </div>
        </div>
    </div>
</template>
