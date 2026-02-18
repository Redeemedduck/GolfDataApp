"""Backward compatibility — delegates to golf-data-core package.

This shim ensures `import golf_db` and `golf_db.SQLITE_DB_PATH = ...`
both work transparently by proxying attribute access to golf_data.db.
"""
import os
import sys
import types

import golf_data.db as _real_db
from automation.naming_conventions import normalize_with_context

# Configure default path and the full two-tier normalization for GolfDataApp
_real_db.configure(
    sqlite_db_path=os.path.join(os.path.dirname(__file__), 'golf_stats.db'),
    normalize_fn=normalize_with_context,
)


class _GolfDBProxy(types.ModuleType):
    """Module proxy that delegates attribute access to golf_data.db."""

    def __getattr__(self, name):
        return getattr(_real_db, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            setattr(_real_db, name, value)

    def __dir__(self):
        return dir(_real_db)


# Replace this module in sys.modules with the proxy
_proxy = _GolfDBProxy(__name__)
_proxy.__file__ = __file__
_proxy.__path__ = []
_proxy.__package__ = __name__
sys.modules[__name__] = _proxy
