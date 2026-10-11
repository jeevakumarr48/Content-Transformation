"""Generation facade. Providers and format-specific strategy stay behind this boundary."""

from .transformation_engine import generate_output

__all__ = ["generate_output"]
