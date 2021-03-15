// Shamelessly stolen from:
// https://ncjamieson.com/how-to-write-delayuntil/

import { concat, Observable, Subscription } from "rxjs";
import { publish } from "rxjs/operators";

// prettier-ignore
// export const delayUntil = notifier => {
//     return publish((published) => {

//         const delayed = published.pipe(
//             buffer(notifier),
//             take(1),
//             mergeAll()
//         );

//         return concat(delayed, published);
//     })
// }

export const delayUntil = (notifier) => {
    return publish((published) => {
        const delayed = new Observable((subscriber) => {
            let buffering = true;
            const buffer = [];
            const subscription = new Subscription();

            subscription.add(
                notifier.subscribe(
                    () => {
                        buffer.forEach((value) => subscriber.next(value));
                        subscriber.complete();
                    },
                    (error) => subscriber.error(error),
                    () => {
                        buffering = false;
                        buffer.length = 0;
                    }
                )
            );

            subscription.add(
                published.subscribe(
                    (value) => buffering && buffer.push(value),
                    (error) => subscriber.error(error)
                )
            );

            subscription.add(() => {
                buffer.length = 0;
            });

            return subscription;
        });
        return concat(delayed, published);
    });
};
