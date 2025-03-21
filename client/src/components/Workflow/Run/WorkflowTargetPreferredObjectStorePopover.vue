<template>
    <b-popover :target="target" triggers="hover" placement="bottomleft" boundary="window">
        <template v-slot:title>{{ title }}</template>
        <div class="popover-wide">
            <p v-if="invocationPreferredObjectStoreId">存储位置已在调用级别设置。</p>
            <ShowSelectedObjectStore
                v-if="invocationPreferredObjectStoreId"
                :preferred-object-store-id="invocationPreferredObjectStoreId"
                for-what="Galaxy 将默认存储此工具运行的输出在">
            </ShowSelectedObjectStore>
            <div v-else>
                尚未为此工作流调用进行选择。将使用历史记录、用户或 Galaxy 的默认设置。
            </div>
            <div v-localize>
                通过点击工作流运行标题中的存储按钮更改 {{ preferredOrEmptyString }} 存储位置。
            </div>
        </div>
    </b-popover>
</template>

<script>
import showTargetPopoverMixin from "components/ObjectStore/showTargetPopoverMixin";

export default {
    mixins: [showTargetPopoverMixin],
    props: {
        invocationPreferredObjectStoreId: {
            type: String,
            default: null,
        },
        target: {
            type: String,
            required: true,
        },
    },
};
</script>

<style scoped lang="scss">
.popover-wide {
    max-width: 30rem;
}
</style>
