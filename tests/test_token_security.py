import unittest

from utils import helpers


class TokenSecurityTests(unittest.TestCase):
    def setUp(self):
        self.original_key = helpers.SECRET_KEY
        helpers.SECRET_KEY = "a" * 32

    def tearDown(self):
        helpers.SECRET_KEY = self.original_key

    def test_each_token_has_a_unique_session_identifier(self):
        first = helpers.decode_token(helpers.create_access_token({"sub": "student@example.com"}))
        second = helpers.decode_token(helpers.create_access_token({"sub": "student@example.com"}))

        self.assertTrue(first["sid"])
        self.assertNotEqual(first["sid"], second["sid"])


if __name__ == "__main__":
    unittest.main()
