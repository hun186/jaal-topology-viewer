"""Local-only capacity defaults must never leak into hosted WSGI."""
import unittest
from app import _large_local_cases_enabled


class LocalLargeCaseDefaults(unittest.TestCase):
    def test_auto_for_local_flask_cli_without_explicit_variable(self):
        self.assertTrue(_large_local_cases_enabled({
            "FLASK_RUN_FROM_CLI": "true"
        }))
        self.assertTrue(_large_local_cases_enabled({
            "FLASK_RUN_FROM_CLI": "true",
            "JAAL_ENABLE_LARGE_LOCAL": "1",
        }))
        self.assertFalse(_large_local_cases_enabled({
            "FLASK_RUN_FROM_CLI": "true",
            "JAAL_ENABLE_LARGE_LOCAL": "0",
        }))

    def test_no_public_wsgi_or_automated_ci_default(self):
        self.assertFalse(_large_local_cases_enabled({}))
        self.assertFalse(_large_local_cases_enabled({"CI": "true",
                                                     "FLASK_RUN_FROM_CLI": "true"}))
        self.assertFalse(_large_local_cases_enabled({
            "VERCEL": "1",
            "JAAL_ENABLE_LARGE_LOCAL": "1",
            "FLASK_RUN_FROM_CLI": "true",
        }))
        self.assertFalse(_large_local_cases_enabled({"VERCEL_ENV": "production"}))

    def test_opt_in_remains_for_local_non_cli_consumers(self):
        self.assertTrue(_large_local_cases_enabled({"JAAL_ENABLE_LARGE_LOCAL": "1"}))
        self.assertFalse(_large_local_cases_enabled({"JAAL_ENABLE_LARGE_LOCAL": "other"}))


if __name__ == "__main__":
    unittest.main()
