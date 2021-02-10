/* a very simple directive that alerts parent when its height changes */

const doUpdate = (label) => (el, binding) => {
    const handler = binding.value;
    handler(el.clientHeight, binding.modifiers);
};

export const Resize = {
    bind: doUpdate("bind"),
    componentUpdated: doUpdate("componentUpdated"),
};

export default Resize;
