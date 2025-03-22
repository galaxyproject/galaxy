import { getGalaxyInstance } from "app";
import _l from "utils/localization";

export const getUserPreferencesModel = (user_id) => {
    const Galaxy = getGalaxyInstance();
    const config = Galaxy.config;
    user_id = user_id || Galaxy.user.id;
    return {
        information: {
            title: _l("管理信息"),
            id: "edit-preferences-information",
            description:
                config.enable_account_interface && !config.use_remote_user
                    ? _l("编辑您的电子邮箱、地址和自定义参数，或更改您的公开名称。")
                    : _l("编辑您的自定义参数。"),
            url: `/api/users/${user_id}/information/inputs`,
            icon: "fa-user",
            redirect: "/user",
        },
        password: {
            title: _l("修改密码"),
            id: "edit-preferences-password",
            description: _l("允许您更改登录凭据。"),
            icon: "fa-unlock-alt",
            url: `/api/users/${user_id}/password/inputs`,
            submit_title: "保存密码",
            redirect: "/user",
            disabled: config.use_remote_user || !config.enable_account_interface,
        },
        toolbox_filters: {
            title: _l("管理工具箱筛选器"),
            id: "edit-preferences-toolbox-filters",
            description: _l("通过显示或隐藏工具集来自定义您的工具箱。"),
            url: `/api/users/${user_id}/toolbox_filters/inputs`,
            icon: "fa-filter",
            submitTitle: "保存筛选器",
            redirect: "/user",
            disabled: !config.has_user_tool_filters,
        },
    };
};
