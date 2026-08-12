from backend.src import database

from support import AppTestCase


class DatabaseTests(AppTestCase):
    def test_session_objects_do_not_expire_on_commit(self) -> None:
        self.assertFalse(
            database.AsyncSessionLocal.kw["expire_on_commit"]
        )

    def test_user_deletion_cascades_to_entries(self) -> None:
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(
            self.client.post("/insert", params={"word": "persisted"}).status_code,
            200,
        )

        user_id = self.database_rows(
            "SELECT id FROM users WHERE email = ?",
            ("user@example.com",),
        )[0][0]
        self.execute_sql("DELETE FROM users WHERE id = ?", (user_id,))

        self.assertEqual(
            self.database_rows(
                "SELECT entry FROM dict_entries WHERE user_id = ?",
                (user_id,),
            ),
            [],
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
