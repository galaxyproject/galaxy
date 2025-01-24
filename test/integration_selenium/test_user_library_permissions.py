import os

from galaxy_test.selenium.framework import retry_assertion_during_transitions
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestUserLibraryImport(SeleniumIntegrationTestCase):
    run_as_admin = True
    ensure_registered = True

    @classmethod
    def user_import_dir(cls):
        return cls.temp_config_dir("user_library_import_dir")

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        user_import_dir = cls.user_import_dir()
        config["user_library_import_dir"] = user_import_dir

    @selenium_test
    def test_user_library_import_dir(self):
        # create new user, create user_library_import_dir, create new email-dir, insert a random text file
        email = self.get_user_email()
        current_user_import_dir = os.path.join(self.user_import_dir(), email)
        os.makedirs(current_user_import_dir)
        random_filename = self._get_random_name()
        file = open(f"{current_user_import_dir}/{random_filename}", "w")
        file.write(random_filename)
        file.close()

        # allow user to add new datasets in the newly created library
        self.create_lib_and_permit_adding(email)

        # test importing functionality
        self.libraries_open_with_name(self.name)
        self.assert_num_displayed_items_is(0)
        self.libraries_dataset_import(self.navigation.libraries.folder.labels.from_user_import_dir)
        self.select_dataset_from_lib_import_modal([random_filename])
        self.assert_num_displayed_items_is(1)
        return random_filename, email

    @selenium_test
    def test_user_library_import_dir_warning(self):
        # do not create email-dir, assert just warning
        email = self.get_user_email()
        self.create_lib_and_permit_adding(email)

        self.libraries_open_with_name(self.name)
        self.assert_num_displayed_items_is(0)
        self.libraries_dataset_import(self.navigation.libraries.folder.labels.from_user_import_dir)

        # importing modal should be hidden
        self.wait_for_selector_absent_or_hidden(self.modal_body_selector())

        # assert 'user import folder was not created' warning
        self.components.libraries.folder.alert_not_exists_user_import_dir.wait_for_visible()

    @selenium_test
    def test_user_library_dataset_permissions(self):
        dataset_filename, email = self.test_user_library_import_dir()
        self.logout()
        admin_email = self.admin_login()
        self.libraries_open()
        self.libraries_open_with_name(self.name)

        self.components.libraries.folder.manage_dataset_permissions_btn(name=dataset_filename).wait_for_and_click()
        self.components.libraries.folder.make_private_btn.wait_for_and_click()
        access_dataset_roles = self.components.libraries.folder.access_dataset_roles.wait_for_visible()

        assert access_dataset_roles.text == admin_email

        self.components.libraries.folder.btn_open_parent_folder(folder_name=self.name).wait_for_and_click()
        self.components.libraries.folder.private_dataset_icon.wait_for_visible()
        self.logout()
        self.submit_login(email=email)
        self.libraries_open()
        self.libraries_open_with_name(self.name)
        self.assert_num_displayed_items_is(0)

    def create_lib_and_permit_adding(self, email):
        # logout of the current user, only admin can create new libraries
        self.logout()
        self.admin_login()
        self.create_new_library()
        self.libraries_index_search_for(self.name)
        # open permission manage dialog
        self.components.libraries.permission_library_btn.wait_for_and_click()

        # search for created user and add him to permission field
        self.components.libraries.add_items_permission.wait_for_and_click()
        self.components.libraries.add_items_permission_input_field.wait_for_and_send_keys(email)

        self.select_add_items_permission_option(email)

        # assert that the right email has been saved
        allowed_user_email = self.components.libraries.add_items_permission_field_text.wait_for_text()
        assert allowed_user_email == email
        self.components.libraries.toolbtn_save_permissions.wait_for_and_click()
        # assert that toast message is appearing
        self.components.libraries.folder.toast_msg.wait_for_visible()

        self.logout()
        # login back to the 'regular' user account
        self.submit_login(email=email)

    @retry_assertion_during_transitions
    def select_add_items_permission_option(self, option_text):
        el = self.components.libraries.add_items_permission_option.wait_for_clickable()
        assert option_text == el.text
        el.click()
