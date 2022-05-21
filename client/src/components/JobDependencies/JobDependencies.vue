<template>
    <CurrentUser v-if="dependencies && dependencies.length > 0" v-slot="{ user }">
        <div>
            <h3>Job Dependencies</h3>
            <table class="tabletip">
                <thead>
                    <tr>
                        <th>Dependency</th>
                        <th>Dependency Type</th>
                        <th>Version</th>
                        <th v-if="user.is_admin">Path</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(dependency, index) in dependencies" :key="index">
                        <td>${{ dependency.name }}</td>
                        <td>${{ dependency.dependency_type }}</td>
                        <td>${{ dependency.version }}</td>
                        <td v-if="user.is_admin">
                            <div v-if="dependency.environment_path">{{ dependency.environment_path }}</div>
                            <div v-else-if="dependency.path">{{ dependency.path }}</div>
                            <div v-else></div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </CurrentUser>
</template>

<script>
import CurrentUser from "components/providers/CurrentUser";

export default {
    components: {
        CurrentUser,
    },
    props: {
        dependencies: {
            type: Array,
            required: true,
        },
    },
};
</script>
