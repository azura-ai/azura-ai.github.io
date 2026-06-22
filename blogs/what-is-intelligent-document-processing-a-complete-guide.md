# What is Intelligent Document Processing? A Complete Guide
> Intelligent Document Processing (IDP) leverages Large Language Models and agentic workflows to transform unstructured documents into validated, machine-readable data structures.

## Introduction

Enterprise data is predominantly unstructured. Estimates suggest that over 80% of corporate information is trapped in PDFs, scanned images, emails, and handwritten notes. Traditional Optical Character Recognition (OCR) systems, while capable of converting images to text, fail to understand the semantic context or the underlying structure of the data they extract. This gap results in high manual verification costs and brittle automation pipelines that break when a document layout changes.

Intelligent Document Processing (IDP) is the technical solution to this problem. Unlike legacy OCR, which relies on rigid templates and regular expressions, modern IDP utilizes Vision Language Models (VLMs) and agentic frameworks to interpret documents as a human would, but at machine scale. By combining Pydantic for data validation and LangGraph for stateful orchestration, developers can build resilient systems that handle complex extraction tasks with high precision.

This guide explores the architectural components of an IDP system and provides a technical implementation using Pydantic AI and LangGraph.

## Objectives

By the end of this tutorial, you will:
1. Understand the architectural shift from template-based OCR to LLM-driven IDP.
2. Implement a structured data extraction agent using Pydantic AI.
3. Build a stateful document processing workflow with LangGraph to handle validation and retries.
4. Evaluate the performance trade-offs between traditional and agentic IDP approaches.

## Prerequisites

To follow this tutorial, you require the following tools and environment:
- **Python 3.12+**: The latest stable version of Python is recommended for better type hinting and performance. [Python Downloads](https://www.python.org/downloads/)
- **Pydantic AI**: A library for building production-grade AI agents with strict schema enforcement. [Pydantic AI Documentation](https://ai.pydantic.dev/)
- **LangGraph**: A library for building stateful, multi-agent applications. [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- **OpenAI or Google Gemini API Key**: Access to a Vision-capable LLM (e.g., `gpt-4o` or `gemini-1.5-pro`).
- **Docker**: For containerizing the final application. [Docker Documentation](https://docs.docker.com/get-docker/)

## The Evolution of Document Processing

To understand IDP, we must categorize the evolution of document handling into three distinct phases.

### Phase 1: Traditional OCR
Traditional OCR (e.g., Tesseract, early ABBYY) focuses on character recognition. It maps pixels to glyphs. The output is a "bag of words" or a string of text with basic coordinate data. Developers must write complex post-processing logic—often thousands of lines of Regex—to find specific fields like "Invoice Total" or "Patient Name." If the document layout shifts by 10 pixels, the extraction often fails.

### Phase 2: Template-Based Extraction
Systems like Amazon Textract or Azure Form Recognizer introduced layout awareness. They can identify tables and forms. However, they still struggle with "unseen" layouts. If a company receives invoices from 500 different vendors, creating and maintaining 500 templates is operationally unsustainable.

### Phase 3: Agentic IDP
Agentic IDP uses LLMs as the reasoning engine. Instead of looking for a coordinate, the system "reads" the document. It understands that "Amount Due," "Total," and "Balance" might refer to the same data point depending on the context. By using Pydantic AI, we can force the LLM to return data that conforms exactly to a predefined Python class, ensuring type safety and immediate integration with downstream databases.

## Technical Architecture of an IDP System

A production-grade IDP system consists of four primary layers:

1.  **Ingestion Layer**: Handles document normalization (converting PDF, TIFF, and JPEG into a standard format) and image pre-processing (deskewing, denoising).
2.  **Extraction Layer**: The VLM processes the visual and textual data. We use Pydantic AI here to define the "contract" of the output.
3.  **Validation Layer**: Logic that checks the extracted data against business rules (e.g., "Does the sum of line items equal the total?").
4.  **Orchestration Layer**: Managed by LangGraph, this layer handles the flow of data, including human-in-the-loop (HITL) triggers if confidence scores are low.

## Implementation: Building a Structured IDP Agent

In this section, we will implement an agent designed to extract structured data from medical laboratory reports. This requires high precision and strict adherence to a schema.

### Step 1: Environment Setup

Initialize your project and install the necessary dependencies.

```bash
$ mkdir azura-idp-tutorial
$ cd azura-idp-tutorial
$ python -m venv venv
$ source venv/bin/activate
$ pip install pydantic-ai langgraph langchain-openai python-dotenv
```

### Step 2: Defining the Schema

We use Pydantic to define the structure of the data we want to extract. This acts as the "source of truth" for the LLM.

```python
from typing import List, Optional
from pydantic import BaseModel, Field

class LabResult(BaseModel):
    test_name: str = Field(description="The name of the medical test (e.g., Hemoglobin).")
    value: float = Field(description="The numerical value of the result.")
    unit: str = Field(description="The unit of measurement (e.g., g/dL).")
    reference_range: str = Field(description="The normal range for this test.")
    is_abnormal: bool = Field(description="True if the value is outside the reference range.")

class MedicalReport(BaseModel):
    patient_name: str
    date_of_service: str
    provider_name: str
    results: List[LabResult]
    summary: Optional[str] = Field(description="A brief clinical summary of the findings.")
```

### Step 3: Implementing the Pydantic AI Agent

Pydantic AI allows us to wrap the LLM in an `Agent` class that enforces the schema defined above. We use the `result_type` parameter to ensure the output is an instance of `MedicalReport`.

```python
import os
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

load_dotenv()

# Initialize the model
model = OpenAIModel('gpt-4o')

# Define the IDP Agent
idp_agent = Agent(
    model,
    result_type=MedicalReport,
    system_prompt=(
        "You are a specialized medical document processor. "
        "Extract all relevant data from the provided document image or text. "
        "Ensure all numerical values are correctly parsed and abnormal flags are set."
    ),
)

async def extract_document_data(content: str):
    # In a real scenario, 'content' could be a base64 encoded image or raw text
    result = await idp_agent.run(content)
    return result.data
```

### Step 4: Orchestrating with LangGraph

Simple extraction is rarely enough. In enterprise environments, we need a workflow that validates the data and retries the extraction if the schema is violated or if business logic fails. LangGraph provides a `StateGraph` to manage this.

We use a `StateGraph` over a simple loop because it allows for persistent state, fine-grained control over node transitions, and the ability to add human-in-the-loop checkpoints.

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    raw_content: str
    extracted_data: Optional[MedicalReport]
    errors: List[str]
    retry_count: int

def extraction_node(state: AgentState):
    """Node to handle the initial extraction."""
    try:
        # Synchronous wrapper for the async agent call
        import asyncio
        data = asyncio.run(idp_agent.run(state['raw_content']))
        return {"extracted_data": data.data, "errors": []}
    except Exception as e:
        return {"errors": [str(e)], "retry_count": state['retry_count'] + 1}

def validation_node(state: AgentState):
    """Node to validate business logic (e.g., checking if patient name is valid)."""
    data = state['extracted_data']
    errors = []
    
    if not data.patient_name or len(data.patient_name) < 2:
        errors.append("Invalid patient name detected.")
    
    if not data.results:
        errors.append("No lab results found in the document.")
        
    return {"errors": errors}

def should_continue(state: AgentState):
    """Conditional logic to determine the next step."""
    if not state['errors']:
        return "end"
    if state['retry_count'] > 3:
        return "human_intervention"
    return "retry"

# Build the graph
workflow = StateGraph(AgentState)

workflow.add_node("extract", extraction_node)
workflow.add_node("validate", validation_node)

workflow.set_entry_point("extract")

workflow.add_edge("extract", "validate")
workflow.add_conditional_edges(
    "validate",
    should_continue,
    {
        "end": END,
        "retry": "extract",
        "human_intervention": END # In production, route to a manual review queue
    }
)

app = workflow.compile()
```

## Comparison: Traditional vs. Agentic IDP

The following table compares the technical and operational characteristics of traditional OCR-based systems versus Agentic IDP systems powered by LLMs and frameworks like Pydantic AI.

| Feature | Traditional OCR (Template-based) | Agentic IDP (LLM-based) |
| : | : | : |
| **Extraction Logic** | Coordinate-based / Regex | Semantic understanding |
| **Layout Sensitivity** | High (breaks on minor changes) | Low (layout agnostic) |
| **Data Validation** | Manual / Hardcoded rules | Schema-driven (Pydantic) |
| **Development Time** | Weeks (per document type) | Hours (prompt + schema) |
| **Computational Cost** | Low (CPU intensive) | High (Token-based pricing) |
| **Accuracy (Unseen Docs)** | Poor (< 60%) | High (> 90% with proper prompting) |
| **Human-in-the-loop** | Required for most fields | Required only for low-confidence |

## Advanced Considerations in IDP

### Handling Multi-page Documents
When processing documents exceeding 50 pages, context window limits become a constraint. The recommended architectural pattern is to:
1.  **Segment**: Split the PDF into individual pages or logical sections.
2.  **Map**: Run the extraction agent in parallel across all segments.
3.  **Reduce**: Use a secondary "Aggregator Agent" to combine the structured data, resolve duplicates, and ensure cross-page consistency (e.g., a table spanning three pages).

### Vision vs. Text-only Extraction
While many LLMs accept raw text (via OCR pre-processing), Vision Language Models (VLMs) like GPT-4o or Gemini 1.5 Pro perform significantly better on complex layouts. VLMs preserve the spatial relationship between elements, which is critical for understanding nested tables or multi-column forms where the reading order might be ambiguous in a text-only stream.

### Security and Compliance
For industries like Healthcare and Fintech, data residency is paramount. While API-based models offer high performance, local deployments of models like Llama 3 (via vLLM) or specialized IDP models (like Donut or Nougat) may be required to meet GDPR or HIPAA requirements. Implementing a Pydantic AI layer allows for easy switching between cloud APIs and local inference servers without changing the core business logic.

## Conclusion

Intelligent Document Processing represents a fundamental shift from simple character recognition to deep semantic understanding. By utilizing Pydantic AI for structured output and LangGraph for stateful workflow management, developers can build IDP pipelines that are not only more accurate than traditional methods but also significantly more resilient to changes in document formatting. The combination of strict schema enforcement and autonomous retry logic minimizes the need for manual intervention and accelerates the integration of unstructured data into enterprise systems.

Azura AI helps enterprises design and deploy these agentic IDP systems at scale, ensuring high-precision data extraction while maintaining strict GDPR compliance.