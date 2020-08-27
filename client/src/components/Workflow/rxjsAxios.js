import axios from "axios";
import { Subscriber } from "rxjs";
import axiosCancel from "axios-cancel";

axiosCancel(axios);

// inspired by
// https://medium.com/jspoint/working-with-axios-and-rxjs-to-make-simple-ajax-service-module-6fda9ecdaf9f
export class AxiosSubscriber extends Subscriber {
    constructor(observer, url) {
        super(observer);
        // create sample request id
        this.requestId = Math.random() + "-xhr-id";
        // XHR complete pointer
        this.completed = false;
        // make axios request on subscription
        axios
            .get(url, {
                requestId: this.requestId,
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
        if (this.completed === false) {
            axios.cancel(this.requestId);
            this.completed = true;
        }
    }
}
