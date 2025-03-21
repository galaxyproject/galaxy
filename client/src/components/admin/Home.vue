<template>
    <div>
        <h1>管理</h1>

        <p>
            请访问

            <a href="https://galaxyproject.org/admin" target="_blank">Galaxy 管理中心</a> 以了解如何保持您的 Galaxy 处于最佳状态。
        </p>

        <Heading h2 icon="fa-server" size="md">服务器</Heading>
        <ul>
            <li>
                <strong>
                    <router-link to="/admin/data_types">数据类型</router-link>
                </strong>
                - 查看此 Galaxy 中所有可用的数据类型。
            </li>
            <li>
                <strong>
                    <router-link to="/admin/data_tables">数据表</router-link>
                </strong>
                - 查看此 Galaxy 中所有可用的数据表。
            </li>
            <li>
                <strong>
                    <router-link to="/admin/display_applications">显示应用程序</router-link>
                </strong>
                - 查看此 Galaxy 中所有配置的显示应用程序。
            </li>
            <li>
                <strong>
                    <router-link to="/admin/jobs">作业</router-link>
                </strong>
                - 显示所有当前未完成的作业（即其状态为新建、等待、排队或运行中）。管理员可以干净地停止长时间运行的作业。
            </li>
            <li>
                <strong>
                    <router-link to="/admin/data_manager">本地数据</router-link>
                </strong>
                - 管理存储在工具数据表中的参考数据（以及其他数据）。详情请参阅
                <a href="https://galaxyproject.org/admin/tools/data-managers" target="_blank">wiki</a>。
            </li>
            <li>
                <strong>
                    <router-link to="/admin/notifications">通知和广播</router-link>
                </strong>
                - 管理显示给用户的通知和广播消息。
            </li>
        </ul>

        <Heading h2 icon="fa-user" size="md">用户管理</Heading>
        <ul>
            <li>
                <strong>
                    <router-link to="/admin/users">用户</router-link>
                </strong>
                - 主要的用户管理界面，显示与每个用户相关的信息，并提供重置密码、更新用户信息、模拟用户等操作。
            </li>
            <!-- %if trans.app.config.enable_quotas: -->
            <li>
                <strong>
                    <router-link to="/admin/quotas">配额</router-link>
                </strong>
                - 管理用户空间配额。详情请参阅
                <a href="https://galaxyproject.org/admin/disk-quotas" target="_blank">wiki</a>。
            </li>
            <!-- %endif -->
            <li>
                <strong>
                    <router-link to="/admin/groups">用户组</router-link>
                </strong>
                - 查看所有用户组及其成员，并查看每个组的角色。
            </li>
            <li>
                <strong>
                    <router-link to="/admin/roles">角色</router-link>
                </strong>
                - 查看所有非私有角色，包括角色类型以及与角色相关联的用户和组。同时还包括与角色关联的数据集和每个数据集应用的权限。
            </li>
            <li>
                <strong>
                    <router-link to="/admin/forms">表单</router-link>
                </strong>
                - 管理本地表单定义。
            </li>
        </ul>

        <Heading h2 icon="fa-wrench" size="md">工具管理</Heading>
        <ul>
            <li>
                <strong>
                    <router-link to="/admin/sanitize_allow">管理白名单</router-link>
                </strong>
                - 管理已安装工具的输出数据集的 HTML 渲染。
            </li>
            <li v-if="isToolshedInstalled">
                <strong>
                    <router-link to="/admin/toolshed">安装和卸载</router-link>
                </strong>
                - 从工具仓库搜索并安装新工具和其他 Galaxy 工具。详情请参阅
                <a href="https://galaxyproject.org/admin/tools/add-tool-from-toolshed-tutorial" target="_blank">教程</a>。
            </li>
            <li>
                <strong>
                    <router-link to="/admin/reset_metadata">管理元数据</router-link>
                </strong>
                - 选择您希望重置元数据的仓库。
            </li>
        </ul>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faServer, faUser, faWrench } from "@fortawesome/free-solid-svg-icons";

import Heading from "components/Common/Heading.vue";

library.add(faServer, faUser, faWrench);

export default {
    components: { Heading },
    props: {
        isToolshedInstalled: {
            type: Boolean,
            default: false,
        },
    },
};
</script>
