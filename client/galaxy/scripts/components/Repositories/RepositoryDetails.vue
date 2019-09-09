<template>
    <div>
        <span v-if="loading">
            <span class="fa fa-spinner fa-spin" />
            Loading installed repository details...
        </span>
        <div v-else>
            <repositorydetails :repo="toolshedRepository" :toolshedUrl="repo.tool_shed_url" />
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
            toolshedRepository: null
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
