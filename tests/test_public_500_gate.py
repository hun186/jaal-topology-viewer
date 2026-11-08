"""Public 500-person case gate; larger local Jaal presets remain local."""
import unittest
from app import _public_500_enabled, _large_local_cases_enabled


class Public500GateTests(unittest.TestCase):
    def test_hosted_can_show_only_fixed_500_with_rollback(self):
        self.assertFalse(_public_500_enabled({}))
        self.assertFalse(_public_500_enabled({"FLASK_RUN_FROM_CLI":"true"}))
        self.assertTrue(_public_500_enabled({"VERCEL":"1"}))
        self.assertTrue(_public_500_enabled({"VERCEL_ENV":"production"}))
        self.assertTrue(_public_500_enabled({"VERCEL_ENV":"preview"}))
        self.assertFalse(_public_500_enabled({
            "VERCEL":"1","JAAL_VERCEL_500_ENABLED":"0",
        }))
        self.assertFalse(_public_500_enabled({
            "VERCEL":"1","JAAL_VERCEL_500_ENABLED":"arbitrary",
        }))
        # A mis-set local flag can never opt the public server into 3k+.
        env={"VERCEL":"1","FLASK_RUN_FROM_CLI":"true",
             "JAAL_ENABLE_LARGE_LOCAL":"1"}
        self.assertFalse(_large_local_cases_enabled(env))
        self.assertTrue(_public_500_enabled(env))


if __name__ == "__main__":
    unittest.main()
