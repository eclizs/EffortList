import asyncio
import ctypes
import unittest
from types import SimpleNamespace

from backend.src import main
from backend.src.init import create_trie_root, init_trie
from backend.src.routers.users import logout
from backend.src.trie_state import (
    discard_root,
    get_root_lock,
    get_trie_words,
)

from support import AppTestCase


class GuestTrieRouteTests(AppTestCase):
    def test_insert_search_duplicate_and_delete(self) -> None:
        self.assertEqual(self.client.get("/search").status_code, 404)

        inserted = self.client.post("/insert", params={"word": "Daily Item"})
        self.assertEqual(inserted.status_code, 200, inserted.text)
        self.assertEqual(
            self.client.get("/search", params={"prefix": "daily"}).json(),
            {"words": ["Daily Item"]},
        )
        self.assertEqual(
            self.client.post("/insert", params={"word": "daily item"}).status_code,
            409,
        )
        self.assertEqual(
            self.client.delete("/delete", params={"word": "DAILY ITEM"}).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/search", params={"prefix": "daily"}).status_code,
            404,
        )

    def test_invalid_and_empty_words_are_rejected(self) -> None:
        self.assertEqual(
            self.client.post("/insert", params={"word": ""}).status_code,
            400,
        )
        self.assertEqual(
            self.client.post("/insert", params={"word": "invalid:word"}).status_code,
            422,
        )
        self.assertEqual(
            self.client.delete("/delete", params={"word": "missing"}).status_code,
            404,
        )

    def test_guest_sessions_have_isolated_roots(self) -> None:
        self.assertEqual(
            self.client.post("/insert", params={"word": "First Guest"}).status_code,
            200,
        )
        first_identity = self.identity_with_prefix("guest:")

        self.client.cookies.clear()
        self.assertEqual(
            self.client.get("/search", params={"prefix": "First"}).status_code,
            404,
        )
        self.assertEqual(
            self.client.post("/insert", params={"word": "Second Guest"}).status_code,
            200,
        )

        guest_identities = [
            identity
            for identity in main.app.state.roots
            if identity.startswith("guest:")
        ]
        self.assertEqual(len(guest_identities), 2)
        self.assertIn(first_identity, guest_identities)

    def test_delete_all_clears_guest_trie(self) -> None:
        for word in ("First", "Second"):
            self.assertEqual(
                self.client.post("/insert", params={"word": word}).status_code,
                200,
            )

        response = self.client.delete("/delete_all")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"message": "Deleted all entries"})
        self.assertEqual(self.client.get("/search").status_code, 404)


class AuthenticatedTrieRouteTests(AppTestCase):
    def test_entries_rebuild_from_database_after_root_is_discarded(self) -> None:
        registered = self.register()
        self.assertEqual(registered.status_code, 201, registered.text)
        self.assertEqual(
            self.client.post("/insert", params={"word": "Persistent Item"}).status_code,
            200,
        )
        identity = self.identity_with_prefix("user:")

        discard_root(main.app, identity)
        response = self.client.get("/search", params={"prefix": "persistent"})

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"words": ["Persistent Item"]})

    def test_entries_repopulate_after_logout_and_login(self) -> None:
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(
            self.client.post("/insert", params={"word": "Welcome Back"}).status_code,
            200,
        )
        identity = self.identity_with_prefix("user:")

        self.assertEqual(self.client.post("/users/logout").status_code, 204)
        self.assertNotIn(identity, main.app.state.roots)
        self.assertEqual(self.login().status_code, 200)

        response = self.client.get("/search", params={"prefix": "welcome"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"words": ["Welcome Back"]})

    def test_authenticated_duplicates_and_deletes_are_case_insensitive(self) -> None:
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(
            self.client.post("/insert", params={"word": "Case Value"}).status_code,
            200,
        )
        self.assertEqual(
            self.client.post("/insert", params={"word": "case value"}).status_code,
            409,
        )
        self.assertEqual(
            self.client.delete("/delete", params={"word": "CASE VALUE"}).status_code,
            200,
        )
        self.assertEqual(
            self.database_rows("SELECT entry FROM dict_entries"),
            [],
        )

    def test_delete_all_commits_database_deletions(self) -> None:
        self.assertEqual(self.register().status_code, 201)
        for word in ("Persistent First", "Persistent Second"):
            self.assertEqual(
                self.client.post("/insert", params={"word": word}).status_code,
                200,
            )

        response = self.client.delete("/delete_all")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.database_rows("SELECT entry FROM dict_entries"), [])

        identity = self.identity_with_prefix("user:")
        discard_root(main.app, identity)
        self.assertEqual(self.client.get("/search").status_code, 404)


class TrieStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.functions = init_trie()
        self.app = SimpleNamespace(
            state=SimpleNamespace(
                roots={},
                root_locks={},
                functions=self.functions,
            )
        )

    def tearDown(self) -> None:
        for identity in list(self.app.state.roots):
            discard_root(self.app, identity)

    def test_get_trie_words_returns_original_values(self) -> None:
        root = create_trie_root()
        self.app.state.roots["guest:test"] = root
        insert = self.functions["insertTrieNode"]

        for word in ("Apple", "Banana"):
            buffer = ctypes.create_string_buffer(word.encode("utf-8"))
            self.assertEqual(insert(ctypes.byref(root), buffer), 201)

        self.assertEqual(get_trie_words(self.app, root), ["Apple", "Banana"])

    def test_locks_are_shared_per_identity_and_serialize_tasks(self) -> None:
        first = get_root_lock(self.app, "guest:first")
        self.assertIs(first, get_root_lock(self.app, "guest:first"))
        self.assertIsNot(first, get_root_lock(self.app, "guest:second"))

        async def check_serialization() -> None:
            entered = asyncio.Event()

            async def contender() -> None:
                async with first:
                    entered.set()

            async with first:
                task = asyncio.create_task(contender())
                await asyncio.sleep(0)
                self.assertFalse(entered.is_set())

            await task
            self.assertTrue(entered.is_set())

        asyncio.run(check_serialization())

    def test_logout_discards_the_users_root(self) -> None:
        identity = "user:1"
        root = create_trie_root()
        self.app.state.roots[identity] = root
        insert = self.functions["insertTrieNode"]
        word = ctypes.create_string_buffer(b"Persistent Item")
        self.assertEqual(insert(ctypes.byref(root), word), 201)
        request = SimpleNamespace(
            app=self.app,
            session={"identity": identity},
        )

        response = asyncio.run(logout(request, identity))

        self.assertEqual(response.status_code, 204)
        self.assertNotIn(identity, self.app.state.roots)
        self.assertEqual(request.session, {})


if __name__ == "__main__":
    unittest.main()
