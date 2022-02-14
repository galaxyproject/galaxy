import config from "config";
import { create } from "rxjs-spy";
import DevToolsPlugin from "rxjs-spy-devtools-plugin";

// initialize spy
let spy = undefined;
export const initSpy = () => {
    if (!config.rxjsDebug || spy) {
        return spy;
    }

    // How to use the rxjs dev panel in chrome:
    // https://github.com/ardoq/rxjs-devtools/tree/master/packages/rxjs-spy-devtools-plugin
    // https://github.com/cartant/rxjs-spy
    console.warn("Installing rxjs spy, only do this in development");
    spy = create();

    const devtoolsPlugin = new DevToolsPlugin(spy, { verbose: false });
    spy.plug(devtoolsPlugin);

    // teardown the spy if we're hot-reloading:
    if (module.hot) {
        if (module.hot) {
            module.hot.dispose(() => {
                spy.teardown();
            });
        }
    }

    return spy;
};
