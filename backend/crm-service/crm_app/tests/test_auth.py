from unittest import TestCase
from unittest.mock import patch

from crm_app import auth


class TestAuth(TestCase):
    @patch("crm_app.auth.get_user_context")
    def test_get_allowed_company_ids_parent_admin(self, mock_get_user_context):
        mock_get_user_context.return_value = {
            "me": {
                "role": "PARENT_ADMIN",
                "companyId": "parent-1",
            },
            "childCompanies": [
                {"id": "child-1"},
                {"id": "child-2"},
            ],
        }

        allowed, role = auth.get_allowed_company_ids("user-1")

        self.assertEqual(role, "PARENT_ADMIN")
        self.assertEqual(allowed, {"child-1", "child-2"})

    @patch("crm_app.auth.get_user_context")
    def test_ensure_can_write_blocks_readonly(self, mock_get_user_context):
        mock_get_user_context.return_value = {
            "me": {
                "role": "READONLY",
                "companyId": "child-1",
            },
            "childCompanies": [],
        }

        with self.assertRaises(ValueError):
            auth.ensure_can_write("user-1")
