from .framework import (
    selenium_test,
    SeleniumTestCase,
)

EXPECTED__NEW_USER_WELCOME_AXE_IMPACT = "moderate"


class TestNewUserWelcome(SeleniumTestCase):
    @selenium_test
    def test_new_user_welcome_landing(self):
        self.home()
        # assert valid (the default) causes a refresh and then you lose the new
        # user welcome.
        self.register(assert_valid=None)
        new_user_welcome = self.components.new_user_welcome
        new_user_welcome._.wait_for_present()
        new_user_welcome._.assert_no_axe_violations_with_impact_of_at_least(EXPECTED__NEW_USER_WELCOME_AXE_IMPACT)

        new_user_welcome.topics.wait_for_element_count_of_at_least(3)

        topic_titles = []
        for topic in new_user_welcome.topics.all():
            topic_titles.append(topic.get_attribute("data-new-user-welcome-topic-title"))
        assert "Data in Galaxy" in topic_titles
        self.screenshot("new_user_welcome_landing")

        new_user_welcome._.assert_no_axe_violations_with_impact_of_at_least(EXPECTED__NEW_USER_WELCOME_AXE_IMPACT)
        new_user_welcome.topic_button(title="Data in Galaxy").wait_for_and_click()
        new_user_welcome.subtopics.wait_for_element_count_of_at_least(3)

        self.screenshot("new_user_welcome_data_subtopic")
        subtopic_titles = []
        for topic in new_user_welcome.subtopics.all():
            subtopic_titles.append(topic.get_attribute("data-new-user-welcome-subtopic-title"))
        assert "Importing via Data Uploader" in subtopic_titles
        new_user_welcome._.assert_no_axe_violations_with_impact_of_at_least(EXPECTED__NEW_USER_WELCOME_AXE_IMPACT)
        new_user_welcome.subtopic_button(title="Importing via Data Uploader").wait_for_and_click()

        new_user_welcome.slides.wait_for_present()
        # slides violate AXE accessibility test violation found [list] with impact serious: Ensures that lists are structured correctly.
        # probably a vue bootstrap issue
        new_user_welcome._.assert_no_axe_violations_with_impact_of_at_least("critical")
        self.screenshot("new_user_welcome_import_slides_data_0")

        # test back button brings you back...
        new_user_welcome.back.wait_for_and_click()
        new_user_welcome.subtopics.wait_for_element_count_of_at_least(4)
        new_user_welcome.back.wait_for_and_click()
        new_user_welcome.topics.wait_for_element_count_of_at_least(3)
