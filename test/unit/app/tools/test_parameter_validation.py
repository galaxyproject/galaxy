from .util import BaseParameterTestCase


class ParameterValidationTestCase(BaseParameterTestCase):
    def test_simple_ExpressionValidator(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="">
    <validator type="expression" message="Not gonna happen">value.lower() == "foo"</validator>
</param>"""
        )
        p.validate("Foo")
        p.validate("foo")
        with self.assertRaisesRegex(ValueError, "Not gonna happen"):
            p.validate("Fop")

    def test_negated_ExpressionValidator(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="10">
    <validator type="expression" message="Not gonna happen" negate="true">value.lower() == "foo"</validator>
</param>
"""
        )
        with self.assertRaisesRegex(ValueError, "Not gonna happen"):
            p.validate("Foo")
        p.validate("Fop")

    def test_boolean_ExpressionValidator(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="">
    <validator type="expression" message="Not gonna happen">value</validator>
</param>"""
        )
        p.validate("Foo")
        with self.assertRaisesRegex(ValueError, "Not gonna happen"):
            p.validate("")

        p = self._parameter_for(
            xml="""
<param name="blah" type="integer" value="">
    <validator type="expression" message="Not gonna happen">value</validator>
</param>"""
        )
        p.validate(3)
        with self.assertRaisesRegex(ValueError, "Not gonna happen"):
            p.validate(0)

    def test_ExpressionValidator_message(self):
        p = self._parameter_for(
            xml="""
<param name="blah" type="text" value="">
    <validator type="expression">value.lower() == "foo"</validator>
</param>"""
        )
        with self.assertRaisesRegex(
            ValueError, r"Value 'Fop' does not evaluate to True for 'value.lower\(\) == \"foo\"'"
        ):
            p.validate("Fop")
        with self.assertRaisesRegex(
            ValueError, r"Validator 'value.lower\(\) == \"foo\"' could not be evaluated on '1'"
        ):
            p.validate(1)
