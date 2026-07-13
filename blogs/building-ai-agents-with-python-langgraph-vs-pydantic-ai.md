# Building AI Agents with Python: LangGraph vs Pydantic AI
> This guide provides a technical comparison and implementation walkthrough of LangGraph and Pydantic AI for developing production-grade agentic workflows.

## Introduction

The transition from simple Large Language Model (LLM) prompts to complex agentic workflows represents a significant shift in AI engineering. While basic Retrieval-Augmented Generation (RAG) systems follow a linear path, autonomous agents require cycles, state management, and robust error handling. Developers are currently faced with two primary architectural choices for building these systems in Python: LangGraph and Pydantic AI.

LangGraph, an extension of the LangChain ecosystem, treats agentic workflows as cyclic graphs. It is designed for complex, stateful multi-agent systems where the flow of execution must be fine-grained and persistent. Conversely, Pydantic AI is a newer, model-agnostic framework that prioritizes type safety, structured data extraction, and developer experience by leveraging Pydantic's validation capabilities.

This tutorial explores the architectural differences between these frameworks and provides implementation examples for both to help you determine which is better suited for your specific enterprise use case.

## Objectives

By the end of this tutorial, you will:
1. Understand the fundamental architectural differences between graph-based and type-safe agent frameworks.
2. Implement a stateful, cyclic agent using LangGraph.
3. Implement a type-safe, tool-calling agent using Pydantic AI.
4. Evaluate framework trade-offs regarding state management, observability, and type safety.

## Prerequisites

To follow this tutorial, you will need:
- Python 3.12 or higher.
- An OpenAI API key or Anthropic API key.
- Basic familiarity with asynchronous Python (`asyncio`).

Install the required dependencies:

```bash
$ pip install langgraph langchain-openai pydantic-ai logfire
```

## Architectural Comparison

Before diving into code, it is essential to understand the philosophical differences between the two libraries.

| Feature | LangGraph | Pydantic AI |
| : | : | : |
| **Core Paradigm** | Cyclic State Machines (Graphs) | Type-safe Functional Agents |
| **State Management** | Built-in persistence with Checkpointers | External/Manual state management |
| **Type Safety** | Relies on Python TypedDict | Native Pydantic model validation |
| **Control Flow** | Explicit nodes and edges | LLM-driven tool calling and loops |
| **Ecosystem** | Deep integration with LangChain | Model-agnostic, works with any LLM |
| **Human-in-the-loop** | Native "breakpoint" support | Manual implementation required |

## Implementation: LangGraph

LangGraph is built on the concept of a `StateGraph`. Every node in the graph represents a function that transforms the current state, and edges define the transition logic. This is particularly useful for "Human-in-the-loop" workflows where the agent must pause for approval or correction.

### Defining the State

In LangGraph, the state is the "source of truth." We define it using a `TypedDict`.

```python
import operator
from typing import Annotated, TypedDict, Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    # The 'messages' key will store the conversation history.
    # Annotated with operator.add to ensure new messages are appended rather than overwritten.
    messages: Annotated[list[BaseMessage], operator.add]
    research_complete: bool
```

### Implementing Nodes and Logic

Nodes are standard Python functions. In this example, we will build a simple researcher that decides whether it has enough information to answer a query.

```python
llm = ChatOpenAI(model="gpt-4o", streaming=True)

def call_model(state: AgentState):
    messages = state['messages']
    response = llm.invoke(messages)
    return {"messages": [response]}

def router(state: AgentState):
    last_message = state['messages'][-1]
    if "FINAL ANSWER" in last_message.content:
        return END
    return "agent"

# Initialize the Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("agent", call_model)

# Set Entry Point
workflow.set_entry_point("agent")

# Add Conditional Edges
workflow.add_conditional_edges(
    "agent",
    router,
    {
        "agent": "agent",
        END: END
    }
)

# Compile the Graph
app = workflow.compile()
```

### Why LangGraph?

The choice of a graph-based approach is driven by the need for **cycles**. Standard LangChain "Chains" are Directed Acyclic Graphs (DAGs). In real-world scenarios, an agent often needs to go back to a previous step—for example, if a tool returns an error or if the LLM determines its initial plan was flawed. LangGraph handles this by allowing edges to point back to previous nodes, maintaining the state throughout the cycle.

## Implementation: Pydantic AI

Pydantic AI, developed by the team behind the Pydantic validation library, focuses on making agents "just Python." It emphasizes type safety and structured output, making it ideal for Intelligent Document Processing (IDP) and high-precision extraction tasks.

### Defining Structured Output

One of Pydantic AI's strengths is the `result_type` parameter, which ensures the agent returns data matching a specific Pydantic model.

```python
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

# Define the structured output schema
class FinancialExtraction(BaseModel):
    company_name: str = Field(description="The name of the entity")
    revenue: float = Field(description="The annual revenue in USD")
    currency: str = Field(default="USD")
    confidence_score: float = Field(ge=0, le=1)

# Initialize the model and agent
model = OpenAIModel('gpt-4o')
agent = Agent(
    model,
    result_type=FinancialExtraction,
    system_prompt="Extract financial data from the provided text accurately.",
)
```

### Dependency Injection and Tools

Pydantic AI introduces a clean way to handle external dependencies (like database connections or API clients) using a `RunContext`.

```python
class DatabaseConn:
    def get_market_cap(self, ticker: str) -> float:
        # Mock database call
        return 150000000.0

@agent.tool
async def lookup_market_cap(ctx: RunContext[DatabaseConn], ticker: str) -> str:
    market_cap = ctx.deps.get_market_cap(ticker)
    return f"The market cap for {ticker} is {market_cap}"

async def run_pydantic_agent():
    deps = DatabaseConn()
    result = await agent.run(
        "What is the revenue and market cap for TechCorp? Text: TechCorp reported 50M revenue.",
        deps=deps
    )
    
    # The result.data is an instance of FinancialExtraction
    print(f"Company: {result.data.company_name}")
    print(f"Revenue: {result.data.revenue}")
    print(f"Confidence: {result.data.confidence_score}")

# To run:
# import asyncio
# asyncio.run(run_pydantic_agent())
```

### Why Pydantic AI?

Pydantic AI excels in environments where **data integrity** is paramount. By using Pydantic models for both input validation and output structuring, developers can catch errors at the boundary of the LLM call rather than deep within the application logic. The dependency injection system also makes unit testing agents significantly easier compared to framework-heavy alternatives.

## Deep Dive: State Management and Persistence

A critical requirement for enterprise agents is the ability to resume a conversation or a multi-step process after a failure or a human intervention.

### LangGraph Persistence
LangGraph provides a `Checkpointer` interface. When you compile a graph with a checkpointer (e.g., using SQLite or Postgres), the framework automatically saves the state after every node execution. This allows for "Time Travel"—the ability to view and even rewind the state to a previous checkpoint.

### Pydantic AI State
Pydantic AI is largely stateless by design. While it handles conversation history within a single `run` or `run_sync` call, persisting that state across different sessions requires the developer to manually save the message history and reload it. This makes Pydantic AI more lightweight but requires more "glue code" for long-running, multi-session agents.

## Choosing the Right Tool

### Use LangGraph when:
- **Complex Control Flow:** Your agent requires multiple loops, conditional branches, and "go-to" logic.
- **Human-in-the-loop:** You need to pause the agent, wait for human approval, and resume from the exact same state.
- **Multi-Agent Orchestration:** You are building a "supervisor" agent that delegates tasks to multiple specialized sub-agents.
- **Long-running Tasks:** You need built-in persistence to handle infrastructure failures during 10-minute agent runs.

### Use Pydantic AI when:
- **Structured Data Extraction:** Your primary goal is to turn unstructured text into validated JSON/Pydantic objects.
- **Type Safety:** You want the benefits of static type checking and IDE autocompletion throughout your agent logic.
- **Simplicity:** You prefer a functional approach over a graph-based abstraction.
- **FastAPI Integration:** You are building a microservice and want a framework that feels native to the modern Python web ecosystem.

## Performance and Scalability Considerations

When deploying these systems at scale, the overhead of the framework becomes a factor.

| Metric | LangGraph | Pydantic AI |
| : | : | : |
| **Cold Start** | Moderate (Graph compilation) | Fast (Class instantiation) |
| **Memory Overhead** | Higher (State object + History) | Lower (Minimal wrapper) |
| **Latency** | Minimal (Framework adds <10ms) | Minimal (Framework adds <5ms) |
| **Observability** | Deep (LangSmith integration) | Standard (Logfire/OpenTelemetry) |

LangGraph's integration with LangSmith provides an out-of-the-box solution for debugging complex traces. Pydantic AI integrates natively with Logfire, providing a highly readable, structured logging experience that is specifically tuned for Pydantic models.

## Advanced Implementation: Multi-Agent Collaboration

In many enterprise scenarios, a single agent is insufficient. Let's look at how LangGraph handles a "Researcher" and "Writer" multi-agent setup.

```python
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

# Define specialized tools
def search_tool(query: str):
    return "Research data about AI agents..."

def writing_tool(content: str):
    return "Formatted report content."

# Create specialized agents
researcher = create_react_agent(llm, tools=[search_tool])
writer = create_react_agent(llm, tools=[writing_tool])

# In LangGraph, you would connect these agents as nodes in a parent graph
def researcher_node(state: AgentState):
    result = researcher.invoke(state)
    return {"messages": [AIMessage(content=result["messages"][-1].content, name="Researcher")]}

def writer_node(state: AgentState):
    result = writer.invoke(state)
    return {"messages": [AIMessage(content=result["messages"][-1].content, name="Writer")]}

# The parent graph manages the handoff logic
builder = StateGraph(AgentState)
builder.add_node("researcher", researcher_node)
builder.add_node("writer", writer_node)
builder.add_edge("researcher", "writer")
builder.set_entry_point("researcher")
multi_agent_app = builder.compile()
```

This modularity allows teams to develop and test individual agents independently before integrating them into a larger workflow.

## Conclusion

Both LangGraph and Pydantic AI are powerful tools, but they serve different architectural needs. LangGraph is a robust choice for complex, stateful, and cyclic workflows where the path to a solution is not linear. Pydantic AI is the superior choice for high-precision, type-safe applications where structured data and developer velocity are the priorities.

For enterprises, the choice often comes down to the complexity of the business logic. If you are automating a multi-step logistics process with human checkpoints, LangGraph's state