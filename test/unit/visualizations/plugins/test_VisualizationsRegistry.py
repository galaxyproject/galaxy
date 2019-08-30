"""
Test lib/galaxy/visualization/plugins/registry.
"""
import os
import re
import unittest

from six import text_type

from galaxy import model
from galaxy.visualization.plugins import plugin
from galaxy.visualization.plugins.registry import VisualizationsRegistry
from ...unittest_utils import galaxy_mock, utility

glx_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir))
template_cache_dir = os.path.join(glx_dir, 'database', 'compiled_templates')
addtional_templates_dir = os.path.join(glx_dir, 'config', 'plugins', 'visualizations', 'common', 'templates')
vis_reg_path = 'config/plugins/visualizations'

config1 = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE visualization SYSTEM "../../visualization.dtd">
<visualization name="scatterplot">
    <data_sources>
        <data_source>
            <model_class>HistoryDatasetAssociation</model_class>
            <test type="isinstance" test_attr="datatype" result_type="datatype">tabular.Tabular</test>
            <to_param param_attr="id">dataset_id</to_param>
        </data_source>
    </data_sources>
    <params>
        <param type="dataset" var_name_in_template="hda" required="true">dataset_id</param>
    </params>
    <template>scatterplot.mako</template>
</visualization>
"""


class VisualizationsRegistry_TestCase(unittest.TestCase):

    def test_plugin_load_from_repo(self):
        """should attempt load if criteria met"""
        mock_app = galaxy_mock.MockApp(root=glx_dir)
        plugin_mgr = VisualizationsRegistry(mock_app,
            directories_setting=vis_reg_path,
            template_cache_dir=None)

        expected_plugins_path = os.path.join(glx_dir, vis_reg_path)
        self.assertEqual(plugin_mgr.base_url, 'visualizations')
        self.assertEqual(plugin_mgr.directories, [expected_plugins_path])

        scatterplot = plugin_mgr.plugins['scatterplot']
        self.assertEqual(scatterplot.name, 'scatterplot')
        self.assertEqual(scatterplot.path, os.path.join(expected_plugins_path, 'scatterplot'))
        self.assertEqual(scatterplot.base_url, '/'.join([plugin_mgr.base_url, scatterplot.name]))
        self.assertTrue(scatterplot.serves_templates)
        self.assertEqual(scatterplot.template_path, os.path.join(scatterplot.path, 'templates'))
        self.assertEqual(scatterplot.template_lookup.__class__.__name__, 'TemplateLookup')

        trackster = plugin_mgr.plugins['trackster']
        self.assertEqual(trackster.name, 'trackster')
        self.assertEqual(trackster.path, os.path.join(expected_plugins_path, 'trackster'))
        self.assertEqual(trackster.base_url, '/'.join([plugin_mgr.base_url, trackster.name]))
        self.assertFalse(trackster.serves_templates)

    def test_plugin_load(self):
        """"""
        mock_app_dir = galaxy_mock.MockDir({
            'plugins': {
                'vis1': {
                    'config': {
                        'vis1.xml': config1
                    },
                    'static': {},
                    'templates': {},
                },
                'vis2': {
                    'config': {
                        'vis2.xml': config1
                    }
                },
                'not_a_vis1': {
                    'config': {
                        'vis1.xml': 'blerbler'
                    },
                },
                # empty
                'not_a_vis2': {},
                'not_a_vis3': 'blerbler',
                # bad config
                'not_a_vis4': {
                    'config': {
                        'not_a_vis4.xml': 'blerbler'
                    }
                },
                'not_a_vis5': {
                    # no config
                    'static': {},
                    'templates': {},
                },
            }
        })
        mock_app = galaxy_mock.MockApp(root=mock_app_dir.root_path)
        plugin_mgr = VisualizationsRegistry(mock_app,
            directories_setting='plugins',
            template_cache_dir=template_cache_dir)

        expected_plugins_path = os.path.join(mock_app_dir.root_path, 'plugins')
        expected_plugin_names = ['vis1', 'vis2']

        self.assertEqual(plugin_mgr.base_url, 'visualizations')
        self.assertEqual(plugin_mgr.directories, [expected_plugins_path])
        self.assertEqual(sorted(plugin_mgr.plugins.keys()), expected_plugin_names)

        vis1 = plugin_mgr.plugins['vis1']
        self.assertEqual(vis1.name, 'vis1')
        self.assertEqual(vis1.path, os.path.join(expected_plugins_path, 'vis1'))
        self.assertEqual(vis1.base_url, '/'.join([plugin_mgr.base_url, vis1.name]))
        self.assertTrue(vis1.serves_templates)
        self.assertEqual(vis1.template_path, os.path.join(vis1.path, 'templates'))
        self.assertEqual(vis1.template_lookup.__class__.__name__, 'TemplateLookup')

        vis2 = plugin_mgr.plugins['vis2']
        self.assertEqual(vis2.name, 'vis2')
        self.assertEqual(vis2.path, os.path.join(expected_plugins_path, 'vis2'))
        self.assertEqual(vis2.base_url, '/'.join([plugin_mgr.base_url, vis2.name]))
        self.assertFalse(vis2.serves_templates)

        mock_app_dir.remove()
        template_cache_dir

    def test_interactive_environ_plugin_load(self):
        """
        """
        jupyter_config = utility.clean_multiline_string("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE interactive_environment SYSTEM "../../interactive_environments.dtd">
        <interactive_environment name="Jupyter">
            <data_sources>
                <data_source>
                    <model_class>HistoryDatasetAssociation</model_class>
                    <test type="isinstance" test_attr="datatype" result_type="datatype">tabular.Tabular</test>
                    <test type="isinstance" test_attr="datatype" result_type="datatype">data.Text</test>
                    <to_param param_attr="id">dataset_id</to_param>
                </data_source>
            </data_sources>
            <params>
                <param type="dataset" var_name_in_template="hda" required="true">dataset_id</param>
            </params>
            <template>jupyter.mako</template>
        </interactive_environment>
        """)

        mock_app_dir = {
            'plugins': {
                'jupyter': {
                    'config': {
                        'jupyter.xml': jupyter_config
                    },
                    'templates': {}
                },
            },
        }

        # going to use a fake template here to simplify testing
        jupyter_template = "${ ie_request }-${ get_api_key() }"
        mock_app_dir['plugins']['jupyter']['templates']['jupyter.mako'] = jupyter_template
        # so that we don't create a cached version of that fake template in the real mako caches
        #   we'll set up a cache in the temp dir
        mock_app_dir['caches'] = {}
        # and make sure the vis reg uses that
        mock_app_dir = galaxy_mock.MockDir(mock_app_dir)
        mock_app = galaxy_mock.MockApp(root=mock_app_dir.root_path)
        plugin_mgr = VisualizationsRegistry(mock_app,
            directories_setting='plugins',
            template_cache_dir=os.path.join(mock_app_dir.root_path, 'caches'))

        # ...then start testing
        expected_plugins_path = os.path.join(mock_app_dir.root_path, 'plugins')
        expected_plugin_names = ['jupyter']

        self.assertEqual(plugin_mgr.base_url, 'visualizations')
        self.assertEqual(plugin_mgr.directories, [expected_plugins_path])
        self.assertEqual(sorted(plugin_mgr.plugins.keys()), expected_plugin_names)

        jupyter = plugin_mgr.plugins['jupyter']
        config = jupyter.config

        self.assertEqual(jupyter.name, 'jupyter')
        self.assertEqual(config.get('plugin_type'), 'interactive_environment')

        # get_api_key needs a user, fill_template a trans
        user = model.User(email="blah@bler.blah", password="dockerDockerDOCKER")
        trans = galaxy_mock.MockTrans(user=user)
        # use a mock request factory - this will be written into the filled template to show it was used
        jupyter.INTENV_REQUEST_FACTORY = lambda t, p: 'mock'

        # should return the (new) api key for the above user (see the template above)
        response = jupyter._render({}, trans=trans)
        response.strip()
        self.assertIsInstance(response, text_type)
        self.assertTrue('-' in response)
        ie_request, api_key = response.split('-')

        self.assertEqual(ie_request, 'mock')

        match = re.match(r'[a-f0-9]{32}', api_key)
        self.assertIsNotNone(match)
        self.assertEqual(match.span(), (0, 32))

        mock_app_dir.remove()

    def test_script_entry(self):
        """"""
        script_entry_config = utility.clean_multiline_string("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <visualization name="js-test">
            <data_sources>
                <data_source>
                    <model_class>HistoryDatasetAssociation</model_class>
                </data_source>
            </data_sources>
            <entry_point entry_point_type="script" data-main="one" src="bler"></entry_point>
        </visualization>
        """)

        mock_app_dir = galaxy_mock.MockDir({
            'plugins': {
                'jstest': {
                    'config': {
                        'jstest.xml': script_entry_config
                    },
                    'static': {}
                },
            }
        })
        mock_app = galaxy_mock.MockApp(root=mock_app_dir.root_path)
        plugin_mgr = VisualizationsRegistry(mock_app,
            directories_setting='plugins',
            template_cache_dir=template_cache_dir)
        script_entry = plugin_mgr.plugins['jstest']

        self.assertIsInstance(script_entry, plugin.ScriptVisualizationPlugin)
        self.assertEqual(script_entry.name, 'jstest')
        self.assertTrue(script_entry.serves_templates)

        trans = galaxy_mock.MockTrans()
        script_entry._set_up_template_plugin(mock_app_dir.root_path, [addtional_templates_dir])
        response = script_entry._render({}, trans=trans, embedded=True)
        self.assertTrue('src="bler"' in response)
        self.assertTrue('type="text/javascript"' in response)
        self.assertTrue('data-main="one"' in response)
        mock_app_dir.remove()


# -----------------------------------------------------------------------------
# TODO: config parser tests (in separate file)

if __name__ == '__main__':
    unittest.main()
