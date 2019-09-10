<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <span v-if="loading">
                <b-card>
                    <span class="fa fa-spinner fa-spin" />
                    Loading installed repository details...
                </b-card>
            </span>
            <div v-else>
                <repositorydetails :repo="toolshedRepository" :toolshedUrl="repo.tool_shed_url" />
            </div>
        </div>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services.js";
import RepositoryDetails from "components/Toolshed/RepositoryDetails.vue";

export default {
    props: ["repo"],
    components: {
        repositorydetails: RepositoryDetails
    },
    data() {
        return {
            loading: true,
            toolshedRepository: null,
            error: null
        };
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.load();
    },
    methods: {
        load() {
            this.loading = true;
            this.services
                .getRepository(this.repo)
                .then(toolshedRepository => {
                    this.toolshedRepository = toolshedRepository;
                    this.loading = false;
                })
                .catch(error => {
                    this.error = error;
                });
        }
    }
};
</script>
