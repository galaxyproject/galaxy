<template>
    <span class="dependency-resolver">
        <span v-if="dependencyResolver">
            <span v-if="dependencyResolver.resolver_type == 'conda'">
                A Conda dependency resolver was used with prefix <tt>{{ dependencyResolver.prefix }}</tt> and channels
                <tt>{{ dependencyResolver.ensure_channels }}</tt
                >.
                <span v-if="dependencyResolver.use_local">
                    Local Conda packages are enabled for this resolver (this is not best practice for production but may
                    be useful for development).
                </span>
                <span v-else>
                    Local Conda packages are disabled for this resolver (this is best practice for production).
                </span>
            </span>
            <span v-else>
                A dependency resolver of type {{ dependencyResolver.resolver_type }} was used to resolve these
                dependencies.
            </span>
            <display-raw :object="dependencyResolver" />
        </span>
        <span v-else> no dependency resolver </span>
    </span>
</template>
<script>
import DisplayRaw from "./DisplayRaw";

export default {
    components: { DisplayRaw },
    props: {
        dependencyResolver: {
            type: Object,
        },
        compact: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        resolverType: function () {
            return this.dependencyResolver && this.dependencyResolver.resolver_type;
        },
    },
};
</script>
