"""Tests for exceptions module."""

import unittest
from exceptions import (
    GolfDataAppError,
    DatabaseError,
    ModelNotTrainedError,
    ValidationError,
    ConfigurationError,
    RateLimitError,
    AuthenticationError,
)


class TestGolfDataAppError(unittest.TestCase):
    """Tests for the base exception class."""

    def test_basic_message(self):
        e = GolfDataAppError("something went wrong")
        self.assertEqual(str(e), "something went wrong")
        self.assertEqual(e.message, "something went wrong")

    def test_with_details(self):
        e = GolfDataAppError("error", details={"key": "value"})
        self.assertEqual(e.details, {"key": "value"})
        self.assertIn("key=value", str(e))

    def test_empty_details(self):
        e = GolfDataAppError("error")
        self.assertEqual(e.details, {})

    def test_is_exception(self):
        self.assertTrue(issubclass(GolfDataAppError, Exception))


class TestDatabaseError(unittest.TestCase):
    def test_with_operation_and_table(self):
        e = DatabaseError("failed", operation="insert", table="shots")
        self.assertIn("operation=insert", str(e))
        self.assertIn("table=shots", str(e))

    def test_inherits_base(self):
        self.assertTrue(issubclass(DatabaseError, GolfDataAppError))


class TestModelNotTrainedError(unittest.TestCase):
    def test_default_message(self):
        e = ModelNotTrainedError("DistancePredictor")
        self.assertIn("DistancePredictor", str(e))
        self.assertEqual(e.details["model"], "DistancePredictor")

    def test_custom_message(self):
        e = ModelNotTrainedError("X", message="custom msg")
        self.assertEqual(e.message, "custom msg")


class TestValidationError(unittest.TestCase):
    def test_with_field_and_value(self):
        e = ValidationError("bad data", field="carry", value=-5)
        self.assertIn("field=carry", str(e))
        self.assertIn("value=-5", str(e))


class TestConfigurationError(unittest.TestCase):
    def test_with_config_key(self):
        e = ConfigurationError("missing", config_key="GEMINI_API_KEY")
        self.assertIn("config_key=GEMINI_API_KEY", str(e))


class TestRateLimitError(unittest.TestCase):
    def test_with_retry_after(self):
        e = RateLimitError("too fast", retry_after=30.0)
        self.assertEqual(e.details["retry_after_seconds"], 30.0)


class TestAuthenticationError(unittest.TestCase):
    def test_with_provider(self):
        e = AuthenticationError("login failed", provider="uneekor")
        self.assertIn("provider=uneekor", str(e))


class TestExceptionHierarchy(unittest.TestCase):
    """Verify all exceptions inherit from GolfDataAppError."""

    def test_all_subclass_base(self):
        for exc_cls in [
            DatabaseError,
            ModelNotTrainedError,
            ValidationError,
            ConfigurationError,
            RateLimitError,
            AuthenticationError,
        ]:
            self.assertTrue(
                issubclass(exc_cls, GolfDataAppError),
                f"{exc_cls.__name__} should inherit GolfDataAppError"
            )

    def test_catchable_as_base(self):
        try:
            raise DatabaseError("test")
        except GolfDataAppError:
            pass  # Should be caught


if __name__ == "__main__":
    unittest.main()
