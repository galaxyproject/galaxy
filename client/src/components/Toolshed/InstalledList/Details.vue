<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <span v-if="loading">
                <BCard>
                    <LoadingSpan message="Loading installed repository details" />
                </BCard>
            </span>
            <div v-else>
                <RepositoryDetails :repo="toolshedRepository" :toolshed-url="repo.tool_shed_url" />
            </div>
        </div>
    </div>
</template>
<script>
import { BCard } from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import { getAppRoot } from "onload/loadConfig";

import { Services } from "../services";

import RepositoryDetails from "../RepositoryDetails/Index.vue";

export default {
    components: {
        BCard,
        LoadingSpan,
        RepositoryDetails,
    },
    props: {
        repo: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            loading: true,
            toolshedRepository: null,
            error: null,
        };
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services();
        this.load();
    },
    methods: {
        load() {
            this.loading = true;
            this.services
                .getRepositoryByName(this.repo.tool_shed_url, this.repo.name, this.repo.owner)
                .then((toolshedRepository) => {
                    this.toolshedRepository = toolshedRepository;
                    this.loading = false;
                })
                .catch((error) => {
                    this.error = error;
                });
        },
    },
};
</script>
