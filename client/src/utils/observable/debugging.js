/**
 * Rxjs debugging utility
 * See: https://cartant.github.io/rxjs-spy/
 */

// import config from "config";
// import { create } from "rxjs-spy";
// import DevToolsPlugin from "rxjs-spy-devtools-plugin";
import { pipe } from "rxjs";
import { tap } from "rxjs/operators";

// if (config.name == "development") {
//     console.warn(`enabling rxjs-spy in environment: ${config.name}`);
//     console.log("https://cartant.github.io/rxjs-spy/");
//     const spy = create({
//         sourceMaps: true,
//     });
//     const devtoolsPlugin = new DevToolsPlugin(spy, {
//         verbose: false,
//     });
//     spy.plug(devtoolsPlugin);

//     // We must teardown the spy if we're hot-reloading:
//     if (module.hot) {
//         if (module.hot) {
//             module.hot.dispose(() => {
//                 spy.teardown();
//             });
//         }
//     }
// }

/**
 * Creates a logging operator that's toggled via a debug flag.
 * First create a new operator by running the factory:
 *
 * const log = createLogger(true);
 * const warn = createLogger(true, "warn");
 *
 * Then use as an operator in an observable:
 *
 * src$.pipe(
 *      log('whatever value this is'),
 *      warn('this will be a warn instead of log'),
 * )
 *
 * @param {boolean} debug activation flag
 * @param {string} method name of console method
 * @param {string} label Prefix message for console.log
 */
export const createLogger = (debug, method = "log") => (label) =>
    pipe(
        tap((val) => {
            if (debug) {
                console[method](label, val);
            }
        })
    );
