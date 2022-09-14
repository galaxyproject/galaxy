export function getResource() {
    const resource = import("../../../../static/plugins/welcome_page/new_user/dist/static/topics/index");
    return resource.newUserDict;
}
