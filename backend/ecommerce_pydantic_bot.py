from typing import Optional
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from loguru import logger

@dataclass
class CustomerDeps:
    user_id: str
    cart: list[str]

ecommerce_agent = Agent(
    'google-gla:gemini-flash-latest',
    deps_type=CustomerDeps,
    system_prompt=(
        "You are an intelligent Ecommerce assistant. Your goal is to help customers "
        "track their orders, check inventory for specific items, manage their cart, "
        "and complete order bookings securely. Be concise, polite, and heavily rely on "
        "the provided tools to fetch real data before answering."
    )
)

@ecommerce_agent.tool
def get_order_status(ctx: RunContext[CustomerDeps], order_id: str) -> str:
    """Fetch the shipping status of an existing order."""
    logger.info(f"Looking up order {order_id} for user {ctx.deps.user_id}")
    # Mock database lookup
    return f"Order {order_id} is currently Out for Delivery and will arrive by 8 PM."

@ecommerce_agent.tool
def check_inventory(ctx: RunContext[CustomerDeps], product_name: str) -> dict:
    """Check if a specific product is in stock."""
    logger.info(f"Checking inventory for {product_name}")
    # Mock inventory check
    if "laptop" in product_name.lower():
        return {"status": "in_stock", "quantity": 12, "price": 1200.00}
    return {"status": "out_of_stock", "quantity": 0, "restock_date": "Next Tuesday"}

@ecommerce_agent.tool
def initiate_return(ctx: RunContext[CustomerDeps], order_id: str, reason: str) -> str:
    """Initiate a return process for a delivered order."""
    logger.info(f"Initiating return for {order_id}. Reason: {reason}")
    # Mock return processing
    return f"Return authorized for {order_id}. Your shipping label has been emailed."

@ecommerce_agent.tool
def book_order(ctx: RunContext[CustomerDeps], items: list[str], shipping_speed: str) -> dict:
    """Draft a new order booking containing the specified items."""
    logger.info(f"Drafting order booking for user {ctx.deps.user_id} with items: {items}")
    # Mock cart booking transaction
    booking_id = f"BKG-{ctx.deps.user_id[:4]}-9921"
    return {
        "booking_id": booking_id,
        "items": items,
        "shipping": shipping_speed,
        "total_cost": len(items) * 45.00,
        "status": "pending_confirmation"
    }

@ecommerce_agent.tool
def confirm_booking(ctx: RunContext[CustomerDeps], booking_id: str, payment_method: str) -> str:
    """Confirm a drafted booking and execute the charge."""
    logger.info(f"Confirming booking {booking_id} with {payment_method}")
    # Mock payment execution
    return f"Success! Booking {booking_id} has been fully confirmed via {payment_method}. Your items are being prepared."
