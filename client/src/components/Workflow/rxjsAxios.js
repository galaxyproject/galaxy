import axios from "axios";
import { Subscriber } from "rxjs";

// inspired by
// https://medium.com/jspoint/working-with-axios-and-rxjs-to-make-simple-ajax-service-module-6fda9ecdaf9f
// but updated for native axios cancellation
// https://github.com/axios/axios#cancellation
export class AxiosSubscriber extends Subscriber {
    constructor(observer, url) {
        super(observer);
        this.cancel = null;
        // XHR complete pointer
        this.completed = false;
        // make axios request on subscription
        axios
            .get(url, {
                cancelToken: new axios.CancelToken((c) => {
                    this.cancel = c;
                }),
            })
            .then((response) => {
                observer.next(response.data);
                this.completed = true;
                observer.complete();
            })
            .catch((error) => {
                this.completed = true;
                observer.error(error);
            });
    }
    unsubscribe() {
        super.unsubscribe();

        // cancel XHR
        if (this.completed === false && this.cancel !== null) {
            this.cancel();
            this.completed = true;
        }
    }
}
