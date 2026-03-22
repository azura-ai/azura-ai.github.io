# Insurance Card OCR & Eligibility: Real-Time Verification in < 2 Seconds
> Eliminating front-desk friction with localized, high-speed document intelligence for healthcare providers.

## The Challenge
Waiting rooms are clogged by manual data entry. Staff spend 5-10 minutes typing in policy numbers, group IDs, and patient details from physical cards—often with errors that lead to late-cycle denials.

## The Solution: Nexus Card-Agent
A specialized Vision-LLM pipeline that works on mobile devices. Patients snap a photo; the agent extracts all 22+ fields and performs a real-time eligibility check via payer APIs.

<div class="data-flow-viz">
    <div class="flow-node">
        <i class="fas fa-id-card"></i>
        <span>Card Scanner</span>
    </div>
    <div class="process-core">
        <i class="fas fa-eye"></i>
    </div>
    <div class="destination-grid">
        <div class="flow-node mini">
            <i class="fas fa-check-circle"></i>
            <span>Eligibility</span>
        </div>
        <div class="flow-node mini">
            <i class="fas fa-user-md"></i>
            <span>Patient EMR</span>
        </div>
    </div>
</div>

### The Stack
- **Edge Vision**: Mobile-first image enhancement and de-skewing.
- **LLM-Extraction**: Zero-shot field identification (even for obscure regional payers).
- **Validation Logic**: Cross-references against internal patient registries.

| Field | Accuracy (Nexus OCR) | Traditional OCR |
| :--- | :--- | :--- |
| Policy Number | 99.9% | 85% |
| Payor ID | 100% | 82% |
| Complex Logos | Professional | Often Fails |
| Edge Cases | Handled via Agentic Logic | Manual Redirection |

## Implementation Workflow
Patients receive a link via SMS. They capture the card. Within 2 seconds, the data is in the EHR system, and the patient is checked in.

## ROI Impact
One regional hospital group **reduced patient wait times by 65%** and eliminated 100% of data-entry-related claim denials, saving an estimated $450k per year in administrative overhead.
