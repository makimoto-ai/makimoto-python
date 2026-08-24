"""Shared namespace for Makimoto's Python SDKs.

Deliberately holds nothing but the version. `makimoto` is a namespace meant
for multiple products, `kawa` today, others later, each living in its own
subpackage rather than being re-exported here, so adding a second product
never risks a name colliding with the first. Import the product you want
directly:

    from makimoto import kawa
"""

__version__ = "0.1.0"
