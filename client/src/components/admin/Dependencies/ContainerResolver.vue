<template>
    <span class="container-resolver">
        <span v-if="containerResolver" :title="title">
            {{ resolverType }}
            <span v-if="!compact">
                <i>{{ description }}</i>
                <DisplayRaw :object="containerResolver" />
            </span>
        </span>
        <span v-else-if="compact"> </span>
        <span v-else>
            <i>no container resolver</i>
        </span>
    </span>
</template>
<script>
import DisplayRaw from "./DisplayRaw";

export const DESCRIPTION = {
    explicit:
        "这个显式容器解析器会查找标注为工具描述部分的容器——独立于工具需求和配置。",
    mulled: "mulled容器解析器根据工具需求的哈希值获取预构建的Docker容器。",
    mulled_singularity:
        "mulled_singularity容器解析器根据工具需求的哈希值获取预构建的Singularity容器。",
    cached_mulled:
        "cached_mulled容器解析器在服务器上查找已缓存的mulled容器，并通过`docker images`命令发现它们。",
    cached_mulled_singularity:
        "cached_mulled_singularity容器解析器在由服务器挂载的目录中查找已缓存的mulled容器。",
    build_mulled: "",
    build_mulled_cached: "",
};

export default {
    components: { DisplayRaw },
    props: {
        containerResolver: {
            type: Object,
        },
        compact: {
            type: Boolean,
            default: true,
        },
    },
    computed: {
        title: function () {
            return this.compact ? this.description : "";
        },
        description: function () {
            const description = DESCRIPTION[this.resolverType] || `类型为 ${this.resolverType} 的容器解析器。`;
            return `${description}`;
        },
        resolverType: function () {
            return this.containerResolver && this.containerResolver.resolver_type;
        },
    },
};
</script>
