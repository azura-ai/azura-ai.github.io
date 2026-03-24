import os
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from loguru import logger

# 1. State Definition
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str

# 2. Tool Definitions
@tool
def get_order_status(order_id: str) -> str:
    """Fetch the shipping status of an existing order."""
    logger.info(f"Looking up order {order_id} via LangGraph")
    return f"Order {order_id} is currently Out for Delivery and will arrive by 8 PM."

@tool
def check_inventory(product_name: str) -> dict:
    """Check if a specific product is in stock."""
    logger.info(f"Checking inventory for {product_name} via LangGraph")
    if "laptop" in product_name.lower():
        return {"status": "in_stock", "quantity": 12, "price": 1200.00}
    return {"status": "out_of_stock", "quantity": 0, "restock_date": "Next Tuesday"}

@tool
def initiate_return(order_id: str, reason: str) -> str:
    """Initiate a return process for a delivered order."""
    logger.info(f"Initiating return for {order_id} via LangGraph. Reason: {reason}")
    return f"Return authorized for {order_id}. Your shipping label has been emailed."

@tool
def book_order(items: list[str], shipping_speed: str) -> dict:
    """Draft a new order booking containing the specified items."""
    logger.info(f"Drafting order booking via LangGraph with items: {items}")
    booking_id = f"BKG-LANG-9921"
    return {
        "booking_id": booking_id,
        "items": items,
        "shipping": shipping_speed,
        "total_cost": len(items) * 45.00,
        "status": "pending_confirmation"
    }

@tool
def confirm_booking(booking_id: str, payment_method: str) -> str:
    """Confirm a drafted booking and execute the charge."""
    logger.info(f"Confirming booking {booking_id} with {payment_method} via LangGraph")
    return f"Success! Booking {booking_id} has been fully confirmed via {payment_method}. Your items are being prepared."

# 3. Model & Node Definition
tools = [get_order_status, check_inventory, initiate_return, book_order, confirm_booking]

# Setup the Gemini-Flash-Latest Model
llm = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    temperature=0.0
).bind_tools(tools)

def chatbot_node(state: AgentState):
    # LangChain injects a system prompt explicitly if needed, but we can just invoke it.
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

# Define Tool Node using Prebuilt utility
tool_node = ToolNode(tools)

def should_continue(state: AgentState) -> str:
    messages = state["messages"]
    last_message = messages[-1]
    # If there is a tool call, route to tools
    if last_message.tool_calls:
        return "tools"
    return END

# 4. Graph Construction
builder = StateGraph(AgentState)

builder.add_node("chatbot", chatbot_node)
builder.add_node("tools", tool_node)

builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", should_continue, {"tools": "tools", END: END})
builder.add_edge("tools", "chatbot")

ecommerce_graph = builder.compile()

# Example Invocation Wrapper
def run_langgraph_bot(user_id: str, message: str) -> str:
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "user_id": user_id
    }
    final_state = ecommerce_graph.invoke(initial_state)
    return final_state["messages"][-1].content
