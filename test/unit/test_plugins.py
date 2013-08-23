from os import makedirs
from os.path import join, dirname, basename
from tempfile import mkdtemp
from shutil import rmtree

from galaxy.visualization.registry import VisualizationsRegistry


def test_visualization_loading():
    visualizations = __default_viz_root()
    registry = VisualizationsRegistry(visualizations, 'foo')
    assert "VisualizationsRegistry" in str(registry)
    assert visualizations in str(registry)
    assert registry.name == "visualizations"
    __assert_scatterplot_registered(registry)
    assert registry._get_template_paths() == [visualizations]


def test_multiple_visualization_roots():
    temp_dir = mkdtemp()
    try:
        makedirs(join(temp_dir, "coolplugin5"))
        visualization_dirs = "%s,%s" % (__default_viz_root(), temp_dir)
        registry = VisualizationsRegistry(visualization_dirs, 'foo')
        __assert_scatterplot_registered(registry)
        assert "coolplugin5" in \
            [basename(path) for path in registry.get_plugin_directories()]
        assert registry._get_template_paths() == \
            [__default_viz_root(), temp_dir]
    finally:
        rmtree(temp_dir)


def __assert_scatterplot_registered(registry):
    assert 'scatterplot' in \
        [basename(path) for path in registry.get_plugin_directories()]


def __default_viz_root():
    galaxy_root = join(dirname(__file__), '..', '..')
    visualizations = join(galaxy_root, 'config', 'plugins', 'visualizations')
    return visualizations
