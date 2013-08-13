from os.path import join, dirname, basename
from galaxy.visualization.registry import VisualizationsRegistry


def test_visualization_loading():
    galaxy_root = join(dirname(__file__), '..', '..')
    visualizations = join(galaxy_root, 'config', 'plugins', 'visualizations')
    registry = VisualizationsRegistry(visualizations, 'foo')
    assert "VisualizationsRegistry" in str(registry)
    assert visualizations in str(registry)
    assert registry.name == "visualizations"
    assert 'scatterplot' in \
        [basename(path) for path in registry.get_plugin_directories()]
    assert registry._get_template_paths() == [visualizations]
