// Silly, but we don't have another mechanism to access this and using the whole path seems the best approach
const PLUGIN_PATH = "plugins/visualizations/mvpapp";
__webpack_public_path__ = `${window.location.pathname.split(PLUGIN_PATH)[0]}static/${PLUGIN_PATH}/static/dist/`;
