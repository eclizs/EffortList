import unittest

from backend.src import main
from backend.src.crud import parse_admin_csv, parse_user_csv

from support import AppTestCase


class CsvParsingTests(unittest.TestCase):
    def test_repairs_malformed_trailing_quoted_token(self) -> None:
        admin_csv = (
            b'A,C,"Indomie Kaldu Ayam "40"",1,item,1\n'
            b'A,C,"LPG 12kg "ISI"",1,item,1\n'
        )
        user_csv = b'name\n"Indomie Kaldu Ayam "40""\n'

        self.assertEqual(
            parse_admin_csv(admin_csv),
            ['Indomie Kaldu Ayam "40"', 'LPG 12kg "ISI"'],
        )
        self.assertEqual(
            parse_user_csv(user_csv, None),
            ['Indomie Kaldu Ayam "40"'],
        )

    def test_preserves_valid_embedded_quotes(self) -> None:
        contents = b'A,C,"Product ""Special""",1,item,1\n'

        self.assertEqual(parse_admin_csv(contents), ['Product "Special"'])


class AdminImportTests(AppTestCase):
    def upload_csv(self, contents: str):
        preview = self.client.post(
            "/insert_csv/preview",
            files={"file": ("entries.csv", contents, "text/csv")},
        )
        self.assertEqual(preview.status_code, 200, preview.text)

        return self.client.post(
            "/insert_csv",
            json={"entries": preview.json()["entries"]},
        )

    def test_preview_parses_entries_without_inserting_them(self) -> None:
        response = self.client.post(
            "/insert_csv/preview",
            files={
                "file": (
                    "entries.csv",
                    "name\nPreview Apple\nPreview Banana\n",
                    "text/csv",
                )
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {"entries": ["Preview Apple", "Preview Banana"]},
        )
        self.assertEqual(
            self.client.get("/search", params={"prefix": "Preview"}).status_code,
            404,
        )

    def test_admin_can_import_entries_and_duplicates_are_reported(self) -> None:
        registered = self.register(email="admin@example.com")
        self.assertEqual(registered.status_code, 201, registered.text)
        self.execute_sql(
            "UPDATE users SET is_admin = 1 WHERE email = ?",
            ("admin@example.com",),
        )

        response = self.upload_csv(
            "A,C,Imported Apple,1,item,1\n"
            "B,D,Imported Banana,2,item,2\n"
            "C,E,Imported Apple,3,item,3\n"
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {
                "inserted": ["Imported Apple", "Imported Banana"],
                "failed": [
                    {
                        "word": "Imported Apple",
                        "reason": "'Imported Apple' already exists",
                    }
                ],
            },
        )
        self.assertEqual(
            self.database_rows(
                "SELECT entry FROM dict_entries ORDER BY entry"
            ),
            [("Imported Apple",), ("Imported Banana",)],
        )


class ApplicationTests(AppTestCase):
    def test_frontend_and_static_files_are_served(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("<title>EffortList</title>", response.text)
        self.assertIn('class="site-navbar"', response.text)
        self.assertIn('class="site-brand"', response.text)
        self.assertIn('class="feature-guide"', response.text)
        self.assertIn('id="guide-search-title"', response.text)
        self.assertIn('id="guide-add-title"', response.text)
        self.assertIn('id="guide-delete-title"', response.text)
        self.assertIn('data-guide-mode="search"', response.text)
        self.assertIn("Guest session", response.text)
        self.assertIn("js/pages/dictionary.js", response.text)
        self.assertIn('id="csv-preview-dialog"', response.text)
        self.assertIn('id="confirm-upload-btn"', response.text)
        self.assertIn('id="delete-all-dialog"', response.text)
        self.assertIn('id="confirm-delete-all-btn"', response.text)

        stylesheet = self.client.get("/static/style.css")
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("text/css", stylesheet.headers["content-type"])

    def test_login_and_registration_pages_are_served(self) -> None:
        login = self.client.get("/login")
        registration = self.client.get("/register")

        self.assertEqual(login.status_code, 200)
        self.assertIn('data-mode="login"', login.text)
        self.assertIn('autocomplete="current-password"', login.text)
        self.assertEqual(registration.status_code, 200)
        self.assertIn('data-mode="register"', registration.text)
        self.assertIn('autocomplete="new-password"', registration.text)

        for script_path in (
            "/static/js/pages/auth.js",
            "/static/js/pages/dictionary.js",
            "/static/js/core/api.js",
        ):
            with self.subTest(script_path=script_path):
                script = self.client.get(script_path)
                self.assertEqual(script.status_code, 200)
                self.assertIn("javascript", script.headers["content-type"])

    def test_hidden_admin_route_is_not_in_openapi(self) -> None:
        paths = main.app.openapi()["paths"]
        self.assertNotIn("/insert_csv", paths)
        self.assertNotIn("/insert_csv/preview", paths)


if __name__ == "__main__":
    import unittest

    unittest.main()
