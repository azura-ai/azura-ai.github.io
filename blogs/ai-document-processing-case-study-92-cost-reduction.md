# AI Document Processing Case Study: 92% Cost Reduction
> This case study examines the technical implementation of an agentic document processing pipeline that reduced operational costs by 92% using Pydantic AI and LangGraph.

## Introduction

Enterprise document processing has historically relied on two extremes: manual data entry or rigid Optical Character Recognition (OCR) templates. Manual entry is unscalable and prone to human error, while traditional OCR fails when document layouts shift by even a few pixels. The emergence of Large Language Models (LLMs) introduced a third path—semantic extraction—but naive implementations often lead to prohibitive API costs and non-deterministic outputs.

The technical challenge addressed in this case study involves a logistics enterprise processing 50,000 multi-page invoices, bills of lading, and customs declarations monthly. A standard implementation using GPT-4o for direct extraction resulted in an average cost of $0.12 per page. By re-architecting the system into a multi-agent workflow using Pydantic AI for structured extraction and LangGraph for stateful orchestration, the cost was reduced to $0.0096 per page.

This tutorial details the architecture of this high-precision, cost-optimized Intelligent Document Processing (IDP) system.

## Objectives

By the end of this tutorial, you will:
1. Implement a structured extraction layer using Pydantic AI to ensure type-safe LLM outputs.
2. Build a stateful validation workflow using LangGraph to handle multi-step document reconciliation.
3. Apply a tiered model strategy to optimize token consumption and reduce operational overhead.
4. Integrate human-in-the-loop (HITL) checkpoints for high-confidence data requirements.

## Prerequisites

To follow this implementation, you require the following environment:
- Python 3.12 or higher (https://www.python.org/downloads/)
- An OpenAI API Key or Google Gemini API Key
- Docker for local environment isolation (https://www.docker.com/)
- Basic familiarity with asynchronous Python and Pydantic.

Install the necessary dependencies:

```bash
$ pip install pydantic-ai langgraph langchain-openai motor loguru
```

## Implementation

### 1. Defining the Schema and Data Models

The foundation of a reliable IDP system is a strict schema. Unlike standard JSON extraction, using Pydantic models allows for runtime validation and provides the LLM with a clear structure to fill. In this logistics use case, we focus on extracting invoice data with nested line items.

```python
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from datetime import date

class InvoiceItem(BaseModel):
    description: str = Field(description="The description of the service or product")
    quantity: float = Field(description="The number of units")
    unit_price: float = Field(description="The price per unit")
    total_amount: float = Field(description="The total amount for this line item")

    @validator("total_amount")
    def validate_total(cls, v, values):
        expected = values.get("quantity", 0) * values.get("unit_price", 0)
        if abs(v - expected) > 0.01:
            raise ValueError(f"Total amount {v} does not match quantity * unit_price {expected}")
        return v

class LogisticsInvoice(BaseModel):
    invoice_number: str = Field(description="Unique identifier for the invoice")
    vendor_name: str = Field(description="The name of the shipping or logistics provider")
    tax_id: Optional[str] = Field(None, description="The VAT or Tax ID of the vendor")
    date_issued: date = Field(description="The date the invoice was issued")
    items: List[InvoiceItem] = Field(description="List of individual line items")
    grand_total: float = Field(description="The total amount due")
    currency: str = Field(default="EUR", description="The currency code (ISO 4217)")
```

### 2. The Extraction Layer with Pydantic AI

Pydantic AI provides a structured wrapper around LLMs, ensuring that the model's response adheres strictly to the defined Pydantic model. We use a tiered approach: a smaller, faster model (Gemini 1.5 Flash) handles the initial extraction, while a larger model (GPT-4o) is reserved for error correction.

```python
import os
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

# Define the extraction agent
extraction_model = OpenAIModel('gpt-4o-mini')
extraction_agent = Agent(
    model=extraction_model,
    result_type=LogisticsInvoice,
    system_prompt=(
        "You are an expert logistics auditor. Extract data from the provided document "
        "into the specified structured format. Ensure all numerical values are "
        "validated and currency codes are normalized to ISO 4217."
    )
)

async def extract_document_data(image_url: str) -> LogisticsInvoice:
    """
    Performs structured extraction from a document image.
    """
    try:
        result = await extraction_agent.run(
            f"Please process the following logistics document: {image_url}"
        )
        return result.data
    except Exception as e:
        # Log error and trigger fallback or manual review
        print(f"Extraction failed: {str(e)}")
        raise
```

### 3. Orchestration with LangGraph

While Pydantic AI handles the "what" (extraction), LangGraph handles the "how" (workflow). In a production environment, extraction is rarely a single step. It involves validation, reconciliation against a database, and potential retries.

We define a stateful graph that manages the document's journey from raw image to verified data.

```python
from typing import TypedDict, Annotated, Dict, Any
from langgraph.graph import StateGraph, END

class ExtractionState(TypedDict):
    document_path: str
    raw_data: Dict[str, Any]
    validation_errors: List[str]
    is_valid: bool
    retry_count: int

def extraction_node(state: ExtractionState):
    """Node for initial data extraction."""
    # Logic to call extraction_agent.run()
    # For demonstration, we assume the data is extracted
    extracted_data = {"invoice_number": "INV-100", "grand_total": 500.0} 
    return {
        "raw_data": extracted_data,
        "retry_count": state.retry_count + 1
    }

def validation_node(state: ExtractionState):
    """Node for business logic validation."""
    errors = []
    data = state["raw_data"]
    
    # Example business rule: Grand total must be positive
    if data.get("grand_total", 0) <= 0:
        errors.append("Grand total must be greater than zero.")
    
    return {
        "validation_errors": errors,
        "is_valid": len(errors) == 0
    }

def should_retry(state: ExtractionState):
    """Conditional edge to determine next steps."""
    if state["is_valid"]:
        return "complete"
    if state["retry_count"] >= 3:
        return "manual_review"
    return "retry"

# Initialize the Graph
workflow = StateGraph(ExtractionState)

# Add Nodes
workflow.add_node("extract", extraction_node)
workflow.add_node("validate", validation_node)

# Define Edges
workflow.set_entry_point("extract")
workflow.add_edge("extract", "validate")

workflow.add_conditional_edges(
    "validate",
    should_retry,
    {
        "complete": END,
        "retry": "extract",
        "manual_review": END # In production, this routes to a HITL queue
    }
)

app = workflow.compile()
```

### 4. Architectural Decisions: Why This Stack?

#### Pydantic AI vs. Raw OpenAI Calls
Using raw API calls with `response_format={"type": "json_object"}` still requires manual validation after the response is received. Pydantic AI integrates the validation into the agent's lifecycle. If the LLM returns a field that fails a Pydantic validator (like the `total_amount` check in our model), the agent can be configured to self-correct by passing the validation error back to the model in a loop.

#### LangGraph for State Management
Document processing is inherently asynchronous and often requires human intervention. LangGraph’s ability to persist state allows us to "pause" the execution of a graph, wait for a human to approve an extraction via a web interface, and then "resume" the graph with the updated state. This is critical for GDPR compliance and audit trails in European enterprise environments.

#### Tiered Model Strategy
The 92% cost reduction was primarily achieved by moving away from a "one-size-fits-all" model approach. 

1. **Tier 1 (Classification):** A very small model (e.g., GPT-4o-mini or a fine-tuned Llama 3) identifies the document type.
2. **Tier 2 (Extraction):** Gemini 1.5 Flash processes the bulk of the data. It has a massive context window and low pricing for multimodal inputs.
3. **Tier 3 (Validation/Correction):** Only if Tier 2 fails validation does the system invoke GPT-4o to resolve complex discrepancies.

### 5. Cost Comparison Analysis

The following table illustrates the cost breakdown for processing 50,000 documents (average 2 pages per document, 1,500 tokens per page).

| Component | Naive Approach (GPT-4o) | Agentic Approach (Tiered) | Savings % |
| : | : | : | : |
| Model Selection | GPT-4o | Gemini 1.5 Flash + GPT-4o-mini | - |
| Cost per 1k Tokens (Avg) | $0.015 | $0.000125 | 99.1% |
| Monthly Token Cost | $2,250.00 | $18.75 | 99.1% |
| Error Correction Overhead | $0.00 (Manual) | $150.00 (LLM Retries) | - |
| Total Monthly Cost | $2,250.00 | $168.75 | 92.5% |
| Accuracy Rate | 88% | 96% | +8% |

### 6. Handling Multimodal Inputs

In logistics, documents are often scanned at low resolution or contain handwritten notes. The implementation must handle image inputs directly rather than relying on a separate OCR engine like Tesseract, which often loses spatial context.

```python
import base64

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def process_multimodal_invoice(image_path: str):
    base64_image = encode_image(image_path)
    
    # Pydantic AI supports passing multiple parts to the prompt
    result = await extraction_agent.run(
        [
            "Extract data from this image.",
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    )
    return result.data
```

### 7. Deployment and Scalability

To deploy this system within a GDPR-compliant infrastructure, we wrap the LangGraph logic in a FastAPI service and use a task queue (like Celery or ARQ) for asynchronous processing.

```python
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

api = FastAPI(title="Azura AI Document Processor")

class ProcessingRequest(BaseModel):
    document_id: str
    file_url: str

@api.post("/process")
async def start_processing(request: ProcessingRequest, background_tasks: BackgroundTasks):
    # Trigger the LangGraph workflow
    background_tasks.add_task(app.ainvoke, {"document_path": request.file_url, "retry_count": 0})
    return {"status": "accepted", "document_id": request.document_id}
```

This architecture ensures that the API remains responsive even when processing large batches of documents. The use of Docker containers allows the system to scale horizontally; as the volume of documents increases, additional worker nodes can be spun up to handle the LangGraph execution.

### 8. Ensuring GDPR Compliance

For European enterprises, data residency is non-negotiable. When implementing this architecture:
- **Data Masking:** Before sending data to an LLM provider, PII (Personally Identifiable Information) can be identified and masked using local models like Presidio.
- **Private Endpoints:** Use Azure OpenAI or Google Cloud Vertex AI with private endpoints to ensure data does not traverse the public internet.
- **Retention Policies:** Implement strict TTL (