import unittest

from galaxy.datatypes.qiime2 import strip_properties


# Note: Not all the expressions here are completely valid types they are just
# representative examples
class TestStripProperties(unittest.TestCase):
    def test_simple(self):
        simple_expression = 'Taxonomy % Properties("SILVIA")'
        stripped_expression = 'Taxonomy'

        reconstructed_expression = strip_properties(simple_expression)
        self.assertEqual(reconstructed_expression, stripped_expression)

    def test_single(self):
        single_expression = 'FeatureData[Taxonomy % Properties("SILVIA")]'
        stripped_expression = 'FeatureData[Taxonomy]'

        reconstructed_expression = strip_properties(single_expression)
        self.assertEqual(reconstructed_expression, stripped_expression)

    def test_double(self):
        double_expression = ('FeatureData[Taxonomy % Properties("SILVIA"), '
                             'DistanceMatrix % Axes("ASV", "ASV")]')
        stripped_expression = 'FeatureData[Taxonomy, DistanceMatrix]'

        reconstructed_expression = strip_properties(double_expression)
        self.assertEqual(reconstructed_expression, stripped_expression)

    def test_nested(self):
        nested_expression = ('Tuple[FeatureData[Taxonomy % '
                             'Properties("SILVIA")] % Axes("ASV", "ASV")]')
        stripped_expression = 'Tuple[FeatureData[Taxonomy]]'

        reconstructed_expression = strip_properties(nested_expression)
        self.assertEqual(reconstructed_expression, stripped_expression)

    def test_complex(self):
        complex_expression = \
            ('Tuple[FeatureData[Taxonomy % Properties("SILVA")] % Axis("ASV")'
             ', DistanceMatrix % Axes("ASV", "ASV")] % Unique')
        stripped_expression = 'Tuple[FeatureData[Taxonomy], DistanceMatrix]'

        reconstructed_expression = strip_properties(complex_expression)
        self.assertEqual(reconstructed_expression, stripped_expression)

    def test_keep_different_binop(self):
        expression_with_different_binop = \
            ('FeatureData[Taxonomy % Properties("SILVIA"), '
             'Taxonomy & Properties]')
        stripped_expression = \
            'FeatureData[Taxonomy, Taxonomy & Properties]'

        reconstructed_expression = \
            strip_properties(expression_with_different_binop)
        self.assertEqual(reconstructed_expression, stripped_expression)

    def test_multiple_strings(self):
        simple_expression = 'Taxonomy % Properties("SILVIA")'
        stripped_simple_expression = 'Taxonomy'

        reconstructed_simple_expression = strip_properties(simple_expression)

        single_expression = 'FeatureData[Taxonomy % Properties("SILVIA")]'
        stripped_single_expression = 'FeatureData[Taxonomy]'

        reconstructed_single_expression = strip_properties(single_expression)

        self.assertEqual(reconstructed_simple_expression,
                         stripped_simple_expression)
        self.assertEqual(reconstructed_single_expression,
                         stripped_single_expression)

