import { getGalaxyInstance } from "app";
import user from "mvc/user/user-model";
import Masthead from "layout/masthead";
import Modal from "mvc/ui/ui-modal";

export default {

    created() {
        this.initUser();
        this.setFrameClass();
    },

    mounted() {
        this.backboneRender();
    },

    updated() {
        this.backboneRender();
    },
    
    methods: {
        
        backboneRender() {

            // dont bother unless we're in top window
            if (window.top !== window) {
                return;
            }

            let galaxy = getGalaxyInstance();

            // old backbone view
            if (!galaxy.masthead) {
                galaxy.masthead = new Masthead.View(this.$props);
            }
            
            // why is this initialized with the masthead?
            if (!galaxy.modal) {
                galaxy.modal = new Modal.View(); 
            }

            // bolt the rendered DOM onto the vue component's element
            let backboneDom = galaxy.masthead.render();
            this.$el.appendChild(backboneDom.$el[0]);
        },

        // why does this happen in the masthead?
        // Maybe User should be a lazy property somewhere,
        // a separate imported data resource, or an observable?
        initUser() {
            let galaxy = getGalaxyInstance();
            if (!galaxy.user && this.$props.user_json) {
                galaxy.user = new user.User(this.$props.user_json);
            }
        },

        // Alternative to previous manual css manipulation. We don't
        // even need this since :empty is a valid css selector
        
        // TODO: Write style guide outlining the duty of javascript as
        // a manipulator of application state and markup, and not to
        // write CSS manually

        // Going to make this a general init in the onload queue
        setFrameClass() {
            if (window !== window.top) {
                document.body.classList.add("framed");
            }
        }

    }

}
