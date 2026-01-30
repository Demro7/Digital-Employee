"""
Data Models Package for Digital Employee System.

This package contains dataclass models for orders and accounting.

Exports:
    Order: Customer order model.
    OrderItem: Individual item within an order.
    ORDER_SCHEMA: JSON Schema for order validation.
"""

from .order import Order, OrderItem, ORDER_SCHEMA

__all__ = ["Order", "OrderItem", "ORDER_SCHEMA"]
