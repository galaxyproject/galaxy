export async function getResource() {
    const resourceBundle = await import("../../../../static/plugins/welcome_page/new_user/dist/static/topics/index.js");
    return resourceBundle;
}
