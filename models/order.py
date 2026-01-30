"""
Order Data Models and Schemas.

This module defines dataclasses for order management in the Digital Employee system.

Classes:
    OrderItem: Represents a single item within an order.
    Order: Represents a complete customer order with items, status, and customer info.

Constants:
    ORDER_SCHEMA: JSON Schema for API validation and documentation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid
import json


@dataclass
class OrderItem:
    """
    Represents a single item in an order.
    
    Attributes:
        product_id: Unique identifier for the product.
        product_name: Display name of the product.
        quantity: Number of units ordered.
        unit_price: Price per unit in EGP.
        size: Optional size variant (e.g., 'small', 'medium', 'large').
        notes: Optional special instructions for this item.
    """
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    size: Optional[str] = None
    notes: Optional[str] = None
    
    @property
    def subtotal(self) -> float:
        """Calculate subtotal for this item (quantity * unit_price)."""
        return self.quantity * self.unit_price
    
    def to_dict(self) -> dict:
        """Convert item to dictionary representation."""
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "size": self.size,
            "notes": self.notes,
            "subtotal": self.subtotal
        }


@dataclass
class Order:
    """
    Represents a complete customer order.
    
    Attributes:
        sector_id: Business sector identifier (e.g., 'restaurant', 'grocery').
        business_name: Name of the business handling the order.
        items: List of OrderItem objects.
        customer_phone: Customer contact number (Egyptian format: 01XXXXXXXXX).
        customer_name: Customer's name for delivery.
        customer_address: Delivery address.
        order_id: Unique order identifier (auto-generated if not provided).
        status: Order status ('pending', 'confirmed', 'processing', 'completed', 'cancelled').
        created_at: Timestamp when order was created.
        notes: Additional order notes.
    """
    sector_id: str
    business_name: str
    items: List[OrderItem] = field(default_factory=list)
    customer_phone: str = ""
    customer_name: str = ""
    customer_address: str = ""
    order_id: str = field(default_factory=lambda: f"ORD-{uuid.uuid4().hex[:5].upper()}")
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    notes: str = ""
    
    @property
    def total(self) -> float:
        """Calculate total order amount."""
        return sum(item.subtotal for item in self.items)
    
    @property
    def item_count(self) -> int:
        """Get total quantity of all items."""
        return sum(item.quantity for item in self.items)
    
    def add_item(self, item: OrderItem) -> None:
        """Add an item to the order."""
        self.items.append(item)
    
    def remove_item(self, product_id: str) -> None:
        """Remove an item from the order by product_id."""
        self.items = [i for i in self.items if i.product_id != product_id]
    
    def confirm(self) -> None:
        """Mark order as confirmed."""
        self.status = "confirmed"
    
    def cancel(self) -> None:
        """Mark order as cancelled."""
        self.status = "cancelled"
    
    def to_dict(self) -> dict:
        """Convert order to dictionary representation."""
        return {
            "order_id": self.order_id,
            "sector_id": self.sector_id,
            "business_name": self.business_name,
            "items": [item.to_dict() for item in self.items],
            "customer_phone": self.customer_phone,
            "customer_name": self.customer_name,
            "customer_address": self.customer_address,
            "total": self.total,
            "item_count": self.item_count,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "notes": self.notes
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def get_summary(self, lang: str = "en") -> str:
        """Generate order summary string."""
        if lang == "ar":
            lines = [f"📋 ملخص الطلب #{self.order_id}"]
            lines.append("-" * 30)
            for item in self.items:
                lines.append(f"• {item.product_name} x{item.quantity} = {item.subtotal} جنيه")
            lines.append("-" * 30)
            lines.append(f"الإجمالي: {self.total} جنيه")
            if self.customer_phone:
                lines.append(f"📞 {self.customer_phone}")
            if self.customer_address:
                lines.append(f"📍 {self.customer_address}")
        else:
            lines = [f"📋 Order Summary #{self.order_id}"]
            lines.append("-" * 30)
            for item in self.items:
                lines.append(f"• {item.product_name} x{item.quantity} = {item.subtotal} EGP")
            lines.append("-" * 30)
            lines.append(f"Total: {self.total} EGP")
            if self.customer_phone:
                lines.append(f"📞 {self.customer_phone}")
            if self.customer_address:
                lines.append(f"📍 {self.customer_address}")
        
        return "\n".join(lines)


# JSON Schema for Order (for API documentation)
ORDER_SCHEMA = {
    "type": "object",
    "properties": {
        "order_id": {
            "type": "string",
            "pattern": "^ORD-[A-Z0-9]{5}$",
            "description": "Unique order identifier"
        },
        "sector_id": {
            "type": "string",
            "description": "Business sector identifier"
        },
        "business_name": {
            "type": "string",
            "description": "Name of the business"
        },
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "product_name": {"type": "string"},
                    "quantity": {"type": "integer", "minimum": 1},
                    "unit_price": {"type": "number", "minimum": 0},
                    "size": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["product_id", "product_name", "quantity", "unit_price"]
            },
            "minItems": 1
        },
        "customer_phone": {
            "type": "string",
            "pattern": "^01[0-9]{9}$",
            "description": "Egyptian phone number"
        },
        "customer_name": {"type": "string"},
        "customer_address": {"type": "string"},
        "total": {"type": "number"},
        "status": {
            "type": "string",
            "enum": ["pending", "confirmed", "processing", "completed", "cancelled"]
        },
        "created_at": {
            "type": "string",
            "format": "date-time"
        },
        "notes": {"type": "string"}
    },
    "required": ["order_id", "sector_id", "items", "customer_phone"]
}
