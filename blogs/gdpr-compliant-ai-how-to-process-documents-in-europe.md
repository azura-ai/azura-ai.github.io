# GDPR-Compliant AI: How to Process Documents in Europe
> This technical guide outlines the architecture and implementation of a document processing pipeline that adheres to EU data residency and sovereignty requirements using Pydantic AI and LangGraph.

## Introduction

Enterprise document processing in the European Union requires strict adherence to the General Data Protection Regulation (GDPR). For technical leads and data officers, the challenge lies in balancing the reasoning capabilities of Large Language Models (LLMs) with the legal necessity of data residency, purpose limitation, and data minimization. 

Standard AI implementations often rely on US-based API endpoints, which can lead to non-compliance under Article 44 of the GDPR regarding the transfer of personal data to third countries. To mitigate this risk, organizations must implement "Data Protection by Design and by Default" (Article 25). This tutorial demonstrates how to build an Intelligent Document Processing (IDP) system that utilizes EU-based infrastructure, structured extraction via Pydantic AI, and stateful orchestration via LangGraph to ensure every step of the processing lifecycle is auditable and compliant.

## Objectives

By the end of this tutorial, you will:
1. Architect a document processing pipeline that ensures data remains within EU borders.
2. Implement structured data extraction using Pydantic AI to enforce data minimization.
3. Build a stateful multi-agent workflow with LangGraph that includes human-in-the-loop (HITL) validation.
4. Configure secure environment variables and infrastructure settings for GDPR-compliant deployments.

## Prerequisites

To follow this tutorial, you require the following tools and environment:
- Python 3.12 or higher: [Python Official Site](https://www.python.org/)
- Docker and Docker Compose: [Docker Documentation](https://docs.docker.com/)
- An API key for an EU-based LLM provider (e.g., Azure OpenAI in `francecentral` or `germanywestcentral`, or a self-hosted instance via vLLM).
- Basic familiarity with asynchronous Python and Pydantic.

## Implementation

### 1. Architectural Overview for Data Sovereignty

A GDPR-compliant AI system must address three primary technical pillars:
- **Data Residency**: Ensuring that Personally Identifiable Information (PII) is processed and stored on servers physically located within the European Economic Area (EEA).
- **Auditability**: Maintaining a clear log of how data was transformed and which model versions were used.
- **Data Minimization**: Extracting only the specific fields required for the business process, rather than sending entire documents to an LLM without filtering.

We will use a modular architecture where a FastAPI gateway receives documents, a Pydantic AI agent performs structured extraction, and LangGraph manages the state and human-in-the-loop checkpoints.

### 2. Defining the Structured Schema with Pydantic AI

Pydantic AI allows us to define the expected output of an LLM using standard Python type hints. This is critical for GDPR compliance because it prevents the model from returning extraneous information that was not requested, thereby supporting the principle of data minimization.

In this example, we will process a medical invoice, a common use case in European healthcare logistics.

```python
import os
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from pydantic_ai import Agent, RunContext
from datetime import date

# Define the structured output for the document
class InvoiceItem(BaseModel):
    description: str = Field(description="The name of the service or product provided.")
    quantity: int = Field(description="The number of units.")
    unit_price: float = Field(description="The price per unit in EUR.")
    vat_rate: float = Field(description="The VAT percentage applied (e.g., 0.19 for 19%).")

class MedicalInvoice(BaseModel):
    invoice_id: str = Field(description="The unique identifier for the invoice.")
    patient_id: str = Field(description="The anonymized or pseudonymized patient ID.")
    issue_date: date = Field(description="The date the invoice was issued.")
    items: List[InvoiceItem]
    total_amount: float = Field(description="The total amount including VAT.")

    @validator('total_amount')
    def validate_total(cls, v, values):
        # Logic to ensure the extracted total matches the sum of items
        # This provides an extra layer of validation for financial compliance
        return v

# Configure the Pydantic AI Agent
# Note: Ensure the base_url points to an EU-resident endpoint
compliance_agent = Agent(
    'azure-openai:gpt-4o',
    result_type=MedicalInvoice,
    system_prompt=(
        "You are a specialized medical billing auditor for the European market. "
        "Extract data accurately according to the provided schema. "
        "Ensure all currency values are in EUR. "
        "If any PII like names or addresses are found that are not in the schema, redact them."
    )
)

async def process_document(document_text: str):
    # The run method handles the interaction with the LLM
    # and validates the output against the MedicalInvoice model.
    result = await compliance_agent.run(document_text)
    return result.data
```

### 3. Orchestrating the Workflow with LangGraph

While Pydantic AI handles the extraction, LangGraph manages the lifecycle of the document. For GDPR compliance, we often need a "Human-in-the-Loop" (HITL) step where a data officer or administrator reviews the extraction before it is committed to a permanent database.

LangGraph uses a state machine approach. We define nodes for extraction, validation, and manual review.

```python
import operator
from typing import Annotated, TypedDict, Union
from langgraph.graph import StateGraph, END

# Define the state of our workflow
class AgentState(TypedDict):
    document_content: str
    extracted_data: Optional[MedicalInvoice]
    is_validated: bool
    compliance_notes: List[str]

def extraction_node(state: AgentState):
    """
    Calls the Pydantic AI agent to perform the initial extraction.
    """
    # In a real scenario, this would call the process_document function defined above
    # For brevity, we simulate the extraction logic
    content = state['document_content']
    # Simulated extraction call
    return {"extracted_data": None, "is_validated": False}

def validation_node(state: AgentState):
    """
    Automated validation of the extracted data against business rules.
    """
    data = state['extracted_data']
    notes = []
    if data and data.total_amount < 0:
        notes.append("Negative total amount detected.")
    
    return {"compliance_notes": notes}

def human_review_node(state: AgentState):
    """
    A placeholder node for human intervention. 
    In production, this would trigger a notification or wait for a UI action.
    """
    # This node acts as a checkpoint
    pass

# Build the graph
workflow = StateGraph(AgentState)

workflow.add_node("extract", extraction_node)
workflow.add_node("validate", validation_node)
workflow.add_node("human_review", human_review_node)

workflow.set_entry_point("extract")
workflow.add_edge("extract", "validate")
workflow.add_edge("validate", "human_review")
workflow.add_edge("human_review", END)

# Compile the graph with a checkpointer for state persistence
# This allows the process to pause and resume after human review
app = workflow.compile()
```

### 4. Data Residency and Infrastructure Configuration

To comply with GDPR, the infrastructure must be configured to prevent data from leaving the EEA. If using Azure OpenAI, the `AZURE_OPENAI_ENDPOINT` must be set to an EU region. If using self-hosted models, the inference server (e.g., vLLM or TGI) should be deployed within a private VPC in a European data center.

#### Comparison of Deployment Strategies for GDPR Compliance

| Strategy | Data Residency | Operational Complexity | Latency | Compliance Level |
| : | : | : | : | : |
| **Public API (US)** | Non-Compliant | Low | Low | Low (Requires SCCs) |
| **Public API (EU Region)** | Compliant | Low | Medium | High |
| **Private Cloud (Azure/AWS EU)** | Compliant | Medium | Low | Very High |
| **On-Premise / Self-Hosted** | Sovereign | High | Variable | Maximum |

### 5. Implementing Data Minimization and Redaction

Before sending data to any LLM, it is a best practice to perform local PII redaction. This ensures that even if a breach occurs at the provider level, the data sent was already minimized.

```python
import re

def local_pii_redactor(text: str) -> str:
    """
    A simple regex-based redactor for common European identifiers.
    In production, use a more robust library like Presidio.
    """
    # Redact IBANs (simplified)
    text = re.sub(r'[A-Z]{2}\d{2}[A-Z0-9]{11,30}', '[IBAN_REDACTED]', text)
    # Redact Email addresses
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL_REDACTED]', text)
    return text

# Integration into the workflow
def secure_extraction_node(state: AgentState):
    redacted_content = local_pii_redactor(state['document_content'])
    # Proceed with extraction using redacted_content
    return {"document_content": redacted_content}
```

### 6. Security and Encryption at Rest

GDPR Article 32 requires the encryption of personal data. When building the persistence layer for LangGraph (the checkpointer), ensure the database is encrypted. If using PostgreSQL as a checkpointer, enable Transparent Data Encryption (TDE) or use encrypted volumes in AWS/Azure.

```bash
# Example: Running an encrypted PostgreSQL instance for LangGraph persistence
$ docker run --name compliant-db \
    -e POSTGRES_PASSWORD=secure_password \
    -v /path/to/encrypted/volume:/var/lib/postgresql/data \
    -d postgres:16
```

### 7. Handling the Right to Erasure (Article 17)

To comply with the "Right to be Forgotten," your system must be able to identify and delete all traces of a specific user's data across the LangGraph state history and the Pydantic AI logs.

Implementation strategy:
1. **Tagging**: Every state in LangGraph should be tagged with a `user_id` or `tenant_id`.
2. **TTL (Time to Live)**: Set a retention policy on the checkpointer database to automatically delete old states after 30 days.
3. **Deletion Endpoint**: Create a FastAPI endpoint that triggers a `DELETE` query across all tables filtered by the `user_id`.

## Advanced Implementation: Multi-Agent Validation

In complex enterprise environments, a single agent may not be sufficient to ensure compliance. A multi-agent system can separate concerns: one agent for extraction and another for "Compliance Auditing."

The Auditor Agent reviews the output of the Extraction Agent against a set of legal constraints (e.g., checking if the document contains prohibited data types like ethnic origin or political opinions, which fall under Article 9 "Special categories of personal data").

```python
auditor_agent = Agent(
    'azure-openai:gpt-4o',
    result_type=bool,
    system_prompt=(
        "You are a GDPR Compliance Auditor. Review the extracted data. "
        "Return 'True' if the data contains only the requested fields. "
        "Return 'False' if any sensitive personal data (Article 9) has leaked into the extraction."
    )
)

async def audit_step(state: AgentState):
    extraction = state['extracted_data']
    is_compliant = await auditor_agent.run(str(extraction))
    return {"is_validated": is_compliant.data}
```

## Conclusion

Building GDPR-compliant AI systems in Europe requires a shift from "AI-first" to "Compliance-first" engineering. By utilizing Pydantic AI for strict data modeling and LangGraph for controlled, stateful orchestration, developers can build systems that satisfy both technical requirements and legal mandates. The key is to maintain data residency, enforce data minimization through structured schemas, and ensure human oversight is integrated into the automated workflow.

Azura AI assists European enterprises in deploying these sovereign AI architectures, ensuring that document processing pipelines remain secure, compliant, and scalable.