<template>
    <span class="dependency-resolver">
        <span v-if="dependencyResolver">
            <span v-if="dependencyResolver.resolver_type == 'conda'">
                使用了 Conda 依赖解析器，前缀为 <tt>{{ dependencyResolver.prefix }}</tt>，并且使用了以下channel
                <tt>{{ dependencyResolver.ensure_channels }}</tt>
                <span v-if="dependencyResolver.use_local">
                    启用了本地 Conda 包（这对于生产环境并不是最佳实践，但对于开发环境可能很有用）。
                </span>
                <span v-else>
                    禁用了本地 Conda 包（这是生产环境中的最佳实践）。
                </span>
            </span>
            <span v-else>
                使用了类型为 {{ dependencyResolver.resolver_type }} 的依赖解析器来解析这些依赖。
            </span>
            <DisplayRaw :object="dependencyResolver" />
        </span>
        <span v-else>没有依赖解析器</span>
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
