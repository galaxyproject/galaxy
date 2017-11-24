import AdminToolshed from "admin.toolshed";

export function App(options) {
    new AdminToolshed.GalaxyApp(options);
}

window.adminToolshedApp = App;
