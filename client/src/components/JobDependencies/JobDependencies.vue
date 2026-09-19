<template>
    <div v-if="dependencies && dependencies.length > 0">
        <div>
            <Heading id="job-dependencies-heading" h1 separator inline size="md"> Job Dependencies </Heading>
            <table class="tabletip">
                <thead>
                    <tr>
                        <th>Dependency</th>
                        <th>Dependency Type</th>
                        <th>Version</th>
                        <th v-if="currentUser.is_admin">Path</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(dependency, index) in dependencies" :key="index">
                        <td>${{ dependency.name }}</td>
                        <td>${{ dependency.dependency_type }}</td>
                        <td>${{ dependency.version }}</td>
                        <td v-if="currentUser.is_admin">
                            <div v-if="dependency.environment_path">{{ dependency.environment_path }}</div>
                            <div v-else-if="dependency.path">{{ dependency.path }}</div>
                            <div v-else></div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<script>
import { mapState } from "pinia";

import { useUserStore } from "@/stores/userStore";

import Heading from "../Common/Heading.vue";

export default {
    components: { Heading },
    props: {
        dependencies: {
            type: Array,
            required: true,
        },
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
    },
};
</script>
