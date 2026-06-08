# AI Fraud Detection for Payment Processing: A Technical Guide
> This guide demonstrates how to build a multi-agent fraud detection system using LangGraph and Pydantic AI to automate complex risk assessment in payment processing.

## Introduction

Traditional fraud detection systems in the fintech sector primarily rely on static, rule-based engines. While effective for catching known patterns, these systems struggle with "zero-day" fraud tactics and often suffer from high false-positive rates that degrade the user experience. As financial transactions become increasingly complex, particularly within the European regulatory framework (PSD2/PSD3), there is a growing need for systems that can reason across disparate data sources—such as transaction metadata, historical behavior, and document-based identity verification.

This tutorial explores the implementation of an agentic AI architecture for fraud detection. We will move beyond simple classification models to a stateful, multi-step orchestration using LangGraph for workflow control and Pydantic AI for structured data extraction and validation. This approach allows for a "Human-in-the-Loop" (HITL) mechanism, ensuring that high-risk decisions are flagged for manual review while low-risk transactions are processed with sub-second latency.

## Objectives

By the end of this tutorial, you will:
1. Architect a stateful fraud detection pipeline using LangGraph.
2. Implement structured data extraction for financial documents using Pydantic AI.
3. Design a conditional routing logic to handle varying risk levels.
4. Integrate human-in-the-loop validation for high-stakes financial decisions.
5. Deploy the solution within a containerized environment suitable for GDPR-compliant infrastructure.

## Prerequisites

To follow this tutorial, you require the following tools and environment:
- **Python 3.12+**: The latest stable version is recommended for improved type hinting and performance. [Python Downloads](https://www.python.org/downloads/)
- **Docker**: For containerization and local deployment. [Docker Documentation](https://docs.docker.com/)
- **Pydantic AI**: For structured LLM interactions. [Pydantic AI Docs](https://ai.pydantic.dev/)
- **LangGraph**: For managing agentic state and cycles. [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- **FastAPI**: To serve the detection engine as a RESTful API. [FastAPI Docs](https://fastapi.tiangolo.com/)

## Architectural Overview

In a production fintech environment, a fraud detection system must be modular. We avoid a monolithic prompt in favor of a directed acyclic graph (DAG) that can occasionally cycle back for more information.

1.  **Ingestion Layer**: Receives transaction data and associated documents (e.g., invoices or ID photos).
2.  **Extraction Node**: Uses Pydantic AI to convert unstructured document data into validated Python objects.
3.  **Enrichment Node**: Fetches external data, such as IP geolocation or blacklisted wallet addresses.
4.  **Analysis Node**: An LLM-based agent evaluates the combined data against internal risk policies.
5.  **Router**: Determines if the transaction is "Approved," "Rejected," or requires "Manual Review."

## Implementation Step-by-Step

### 1. Project Initialization

First, establish the project structure and install the necessary dependencies.

```bash
$ mkdir azura-fraud-detection
$ cd azura-fraud-detection
$ python -m venv venv
$ source venv/bin/activate
$ pip install pydantic-ai langgraph fastapi uvicorn motor loguru
```

### 2. Defining the Data Schema

Data integrity is paramount in payment processing. We use Pydantic to define the schema for our transaction state. This ensures that every node in our graph receives and emits data that adheres to a strict contract.

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from enum import Enum

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TransactionData(BaseModel):
    transaction_id: str
    amount: float
    currency: str = "EUR"
    merchant_id: str
    user_id: str
    ip_address: str
    timestamp: str

class FraudAnalysis(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    reasoning: List[str]
    flagged_attributes: List[str]
    requires_human_review: bool

class AgentState(BaseModel):
    transaction: TransactionData
    analysis: Optional[FraudAnalysis] = None
    external_data: dict = {}
    current_step: str = "start"
```

### 3. Structured Extraction with Pydantic AI

When processing payments, we often deal with unstructured data like invoice PDFs or transaction memos. Pydantic AI allows us to extract this data with high precision, ensuring the output matches our `TransactionData` model.

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

# Define the model (e.g., GPT-4o or Gemini 1.5 Pro)
model = OpenAIModel('gpt-4o')

# Initialize the Pydantic AI Agent for extraction
extraction_agent = Agent(
    model,
    result_type=TransactionData,
    system_prompt=(
        "You are a specialized financial data extraction agent. "
        "Extract transaction details from the provided text. "
        "Ensure the currency is converted to ISO 4217 format."
    ),
)

async def extract_transaction_details(raw_text: str) -> TransactionData:
    result = await extraction_agent.run(raw_text)
    return result.data
```

### 4. Building the Detection Graph with LangGraph

LangGraph manages the state of the fraud detection process. Unlike a simple chain, LangGraph allows us to define conditional paths. For instance, if the `risk_score` is between 40 and 70, we route to a manual review node instead of an automated rejection.

```python
from langgraph.graph import StateGraph, END
from typing import Dict, TypedDict

class GraphState(TypedDict):
    transaction: TransactionData
    analysis: Optional[FraudAnalysis]
    review_required: bool

def analyze_transaction(state: GraphState):
    """
    Node: Analyze the transaction for fraud patterns.
    """
    tx = state['transaction']
    
    # In a real scenario, this would call an LLM or a specialized ML model.
    # Here we simulate the logic.
    risk_score = 0
    reasons = []
    
    if tx.amount > 10000:
        risk_score += 50
        reasons.append("High transaction volume")
    
    if tx.ip_address.startswith("192.168"): # Mocking a suspicious range
        risk_score += 30
        reasons.append("Suspicious IP range")
        
    level = RiskLevel.LOW
    if risk_score > 70: level = RiskLevel.CRITICAL
    elif risk_score > 40: level = RiskLevel.MEDIUM

    analysis = FraudAnalysis(
        risk_score=risk_score,
        risk_level=level,
        reasoning=reasons,
        flagged_attributes=["amount", "ip_address"] if risk_score > 0 else [],
        requires_human_review=40 <= risk_score <= 70
    )
    
    return {"analysis": analysis, "review_required": analysis.requires_human_review}

def route_decision(state: GraphState):
    """
    Conditional edge to determine the next step.
    """
    if state['review_required']:
        return "human_review"
    if state['analysis'].risk_level == RiskLevel.CRITICAL:
        return "reject"
    return "approve"

# Define the Graph
workflow = StateGraph(GraphState)

# Add Nodes
workflow.add_node("analyze", analyze_transaction)

# Define Edges
workflow.set_entry_point("analyze")

workflow.add_conditional_edges(
    "analyze",
    route_decision,
    {
        "human_review": END, # In production, this would point to a 'wait' state
        "reject": END,
        "approve": END
    }
)

# Compile the Graph
app = workflow.compile()
```

### 5. Handling GDPR and Data Privacy

For European enterprises, GDPR compliance is non-negotiable. When using LLMs for fraud detection, PII (Personally Identifiable Information) must be handled carefully.

- **Data Anonymization**: Before passing the `TransactionData` to the `analyze_transaction` node, sensitive fields like `user_id` or specific `merchant_id` strings should be hashed or tokenized.
- **Local LLM Deployment**: For high-sensitivity data, Azura AI recommends deploying models locally using vLLM or Ollama within a private cloud to ensure data never leaves the sovereign boundary.
- **Audit Logging**: Every decision made by the agent must be logged with the specific version of the prompt and the model used, facilitating the "Right to Explanation" under the AI Act.

## Comparison: Rule-Based vs. Agentic AI Systems

The following table compares traditional fraud detection methods with the agentic approach implemented in this guide.

| Feature | Rule-Based Systems | Traditional ML (XGBoost) | Agentic AI (LangGraph + Pydantic) |
| : | : | : | : |
| **Adaptability** | Low (Manual updates) | Medium (Retraining required) | High (Dynamic reasoning) |
| **Transparency** | High (Boolean logic) | Low (Black box) | High (Natural language reasoning) |
| **False Positive Rate** | High | Medium | Low |
| **Latency** | < 50ms | 100ms - 300ms | 500ms - 2s |
| **Context Awareness** | None | Limited to features | High (Can process documents/memos) |
| **Maintenance** | High (Rule sprawl) | Medium (Data drift) | Low (Policy-based) |

## Advanced Implementation: Human-in-the-Loop (HITL)

In financial systems, an AI should rarely have the final say on a "Critical" or "Medium" risk transaction without an audit trail. LangGraph supports "breakpoints" that allow the graph to pause execution and wait for an external signal (human approval).

When the `route_decision` returns `human_review`, the state is saved to a database (e.g., MongoDB or PostgreSQL). A dashboard used by the risk team fetches these pending states. Once a human reviewer provides an input, the graph resumes from the breakpoint with the new context.

### Example: Resuming State

```python
# This is a conceptual snippet for resuming a LangGraph state
async def process_human_decision(transaction_id: str, decision: str):
    # Fetch the existing state from the checkpointer
    state = await app.get_state(config={"configurable": {"thread_id": transaction_id}})
    
    # Update the state with the human decision
    await app.update_state(
        config={"configurable": {"thread_id": transaction_id}},
        values={"analysis": {"human_override": decision, "status": "resolved"}},
        as_node="human_review"
    )
    
    # Resume execution
    await app.run(None, config={"configurable": {"thread_id": transaction_id}})
```

## Deployment Considerations

To deploy this system for a European enterprise, consider the following stack:
1.  **FastAPI**: Provides the asynchronous interface for transaction ingestion.
2.  **Redis**: Acts as the checkpointer for LangGraph, storing the state of active fraud investigations.
3.  **Worker Nodes**: Use Celery or ARQ to handle the LLM calls out-of-band, ensuring the main API remains responsive.
4.  **Monitoring**: Implement Prometheus and Grafana to track the `risk_score` distribution and latency per node.

### Dockerization

A standard `Dockerfile` for this service should use a non-root user and include health checks to ensure the LLM gateway is reachable.

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN groupadd -g 999 python && \
    useradd -r -u 999 -g python python

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER python

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Conclusion

Building an agentic fraud detection system allows fintech companies to combine the rigor of traditional financial rules with the nuanced reasoning of Large Language Models. By using LangGraph for state management and Pydantic AI for data validation, developers can create resilient, transparent, and highly accurate risk assessment pipelines. This architecture not only reduces the burden on manual review teams but also provides the flexibility needed to adapt to evolving fraud patterns in real-time.

Azura AI assists enterprises in implementing and scaling these agentic architectures within secure, GDPR-compliant environments.