from unittest.mock import MagicMock

from galaxy.webapps.galaxy.services.notifications import NotificationService


def test_failed_confirmation_does_not_fail_the_request():
    admin_request, confirmation, admin_response = MagicMock(), MagicMock(), MagicMock()
    notification_manager = MagicMock()
    notification_manager.send_notification_internal.side_effect = [admin_response, RuntimeError("broker down")]
    request_manager = MagicMock()
    request_manager.build_user_sender_requests.return_value = [admin_request, confirmation]
    service = NotificationService(notification_manager, MagicMock(), request_manager)

    assert service.send_notification(MagicMock(url_builder=None), MagicMock()) is admin_response
    sent = [call.args[0] for call in notification_manager.send_notification_internal.call_args_list]
    assert sent == [admin_request, confirmation]
