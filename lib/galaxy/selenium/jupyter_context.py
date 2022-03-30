from .context import GalaxySeleniumContextImpl
from .context import init as c_init


def init(config=None):
    return c_init(config=config, clazz=JupyterContextImpl)


class JupyterContextImpl(GalaxySeleniumContextImpl):
    def screenshot(self, label):
        path = super().screenshot(label)
        from IPython.display import Image

        return Image(filename=path)
