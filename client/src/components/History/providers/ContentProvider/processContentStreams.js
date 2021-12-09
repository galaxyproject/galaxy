/**
 * General plumbing for the 2 types of content providers. This function returns 3 observables:
 * loading, scrolling, and payload. Payload's the most important and the operator that genrates the
 * payload from the inputs is passed in as a parameter to this factory.
 */
import { distinctUntilChanged, share, startWith, switchMap } from "rxjs/operators";
import { activity, whenAny, show } from "utils/observable";
import { propMatch } from "./helpers";
import { ScrollPos } from "components/History/model/ScrollPos";
import { SearchParams } from "components/providers/History/SearchParams";
import { defaultPayload } from "../ContentProvider";
import { Subject } from "rxjs";

/**
 * Takes incoming history, filters and scroll position and generates loading, scrolling and payload
 * observable for rendering the content. payload$ is an observable that emits the data that should
 * be displaye
 *
 * @param   {function} payloadOperator observable operator that delivers the payload for this list
 * @param   {object}  sources          object containing params$, history$, scrollPos$ source observables
 * @param   {object}  settings         configuration parameter object
 *
 * @return  {object}                   payload$, loading$, scrolling$ observables
 */
// prettier-ignore
export function processContentStreams(payloadOperator, sources = {}, settings = {}) {
    const { debouncePeriod, debug = false } = settings;

    // clean incoming source streams
    const parent$ = sources.parent$.pipe(
        distinctUntilChanged(propMatch("id")),
        show(debug, (parent) => console.log('processContentStreams: parent changed', parent)),
    );
    const params$ = sources.params$.pipe(
        distinctUntilChanged(SearchParams.equals),
        show(debug, (params) => console.log('processContentStreams: params changed', params)),
    );
    const pos$ = sources.scrollPos$.pipe(
        show(debug, (pos) => console.log('processContentStreams: pos changed', pos)),
        distinctUntilChanged(ScrollPos.equals),
    );
    const scrolling$ = sources.scrollPos$.pipe(
        activity(200)
    );

    const loadingEvents$ = new Subject();
    const loading$ = loadingEvents$.pipe(
        activity(debouncePeriod),
        startWith(true)
    );

    const resetPos$ = new Subject();

    // The actual loader, when history or params change we poll against the api and
    // set up a cachewatcher, both of which are controlled by the scroll position
    const loaderReset$ = whenAny(parent$, params$);
    const payload$ = loaderReset$.pipe(
        switchMap(([parent, filters]) => pos$.pipe(
            show(debug, pos => {
                console.clear();
                console.log("processContentStreams: pos", JSON.stringify(pos));
            }),
            payloadOperator({ parent, filters, loadingEvents$, resetPos$, ...settings }),
            startWith({ ...defaultPayload, placeholder: true }),
        )),
        share()
    );

    return { payload$, scrolling$, loading$, resetPos$ };
}
