<template>
    <span class="dependency-resolver">
        <span v-if="dependencyResolver">
            {{ dependencyResolver }}
        </span>
        <span v-else>
            no dependency resolver
        </span>
    </span>
</template>
<script>
export default {
    props: {
        dependencyResolver: {
            type: Object
        },
        compact: {
            type: Boolean,
            default: false
        }
    },
    computed: {
        resolverType: function() {
            return this.dependencyResolver && this.dependencyResolver.resolver_type;
        }
    }
};
</script>
