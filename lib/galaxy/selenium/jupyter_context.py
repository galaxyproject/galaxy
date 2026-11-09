from .context import (
    GalaxySeleniumContextImpl,
    init as c_init,
)


def init(config=None):
    return c_init(config=config, clazz=JupyterContextImpl)


class JupyterContextImpl(GalaxySeleniumContextImpl):
    def screenshot(self, label, caption: str | None = None):
        path = super().screenshot(label, caption)
        from IPython.display import Image

        return Image(filename=path)
