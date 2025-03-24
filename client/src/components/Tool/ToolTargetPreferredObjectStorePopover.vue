<template>
    <b-popover target="tool-storage" triggers="hover" placement="bottomleft" boundary="window">
        <template v-slot:title>{{ title }}</template>
        <div class="popover-wide">
            <p v-if="toolPreferredObjectStoreId">
                已在工具级别设置了{{ preferredOrEmptyString }}存储位置，默认情况下将使用历史或用户偏好设置，如果这些未设置，Galaxy将选择管理员配置的默认值。
            </p>
            <ShowSelectedObjectStore
                v-if="toolPreferredObjectStoreId"
                :preferred-object-store-id="toolPreferredObjectStoreId"
                for-what="Galaxy将默认将此工具运行的输出存储在">
            </ShowSelectedObjectStore>
            <div v-else>
                未为此工具执行做出选择。将使用来自历史、用户或Galaxy的默认设置。
            </div>
            <div v-localize>
                通过点击工具头部的存储按钮更改{{ preferredOrEmptyString }}存储位置。
            </div>
        </div>
    </b-popover>
</template>

<script>
import showTargetPopoverMixin from "components/ObjectStore/showTargetPopoverMixin";

export default {
    mixins: [showTargetPopoverMixin],
    props: {
        toolPreferredObjectStoreId: {
            type: String,
            default: null,
        },
        user: { type: Object, required: true },
    },
};
</script>
<style scoped lang="scss">
.popover-wide {
    max-width: 30rem;
}
</style>
