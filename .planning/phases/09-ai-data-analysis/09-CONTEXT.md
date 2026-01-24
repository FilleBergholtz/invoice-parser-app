# Phase 9: AI Data Analysis - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable users to ask natural language questions about processed invoice data and receive structured answers. This is an optional phase that can be deferred to v3.0.

**Core Problem:** Users want to query and analyze processed invoice data using natural language instead of manually searching Excel files.

**Goal:** Users can ask questions like "What invoices did we receive from Acme Corp in January?" and get structured answers.

</domain>

<decisions>
## Implementation Decisions

### 1. Data Storage

**Approach:**
- Read processed invoices from Excel files (existing export format)
- Or create a simple SQLite database for querying
- Store invoice metadata and line items for retrieval

**Storage Format:**
- Option A: Read from Excel files (simpler, uses existing export)
- Option B: SQLite database (better for querying, requires import step)
- Decision: Start with Excel reading, can add SQLite later

### 2. Query Interface

**Approach:**
- CLI command: `--query "question"`
- Or GUI component (future)
- Natural language input, structured output

**Query Types:**
- Filtering: "invoices from supplier X"
- Aggregation: "total amount for supplier Y"
- Summarization: "summary of invoices in January"
- Comparison: "compare invoices from two suppliers"

### 3. AI Query Processing

**Approach:**
- Use AI (OpenAI/Claude) to parse natural language query
- Extract intent, filters, aggregations
- Convert to structured query or direct data retrieval

**Query Processing:**
- Parse natural language → structured query
- Retrieve relevant invoices
- Process/aggregate data
- Format response

### 4. Response Format

**Approach:**
- Structured JSON or formatted text
- Include relevant invoices, summaries, aggregations
- Present in readable format

</decisions>

<current_state>
## Current Implementation

**Files:**
- `src/export/excel_export.py` - Exports invoices to Excel
- `src/models/invoice_header.py` - InvoiceHeader model
- `src/models/invoice_line.py` - InvoiceLine model
- `src/models/virtual_invoice_result.py` - VirtualInvoiceResult model
- `src/ai/providers.py` - AI provider abstraction (from Phase 8)

**Current Features:**
- Excel export with invoice data
- Invoice models with all fields
- AI provider abstraction ready

**Missing:**
- Invoice data storage/retrieval system
- Query interface
- Natural language query processing
- Response formatting

</current_state>

<requirements>
## Phase Requirements

- **ANALYSIS-01**: User can ask natural language questions about processed invoice data
- **ANALYSIS-02**: System retrieves relevant invoice information based on queries
- **ANALYSIS-03**: System presents query results in structured format
- **ANALYSIS-04**: System can summarize invoice data according to user requests

</requirements>

<research>
## Research References

- `.planning/research/ARCHITECTURE.md`: AI integration patterns
- Phase 8: AI provider abstraction available for query processing

</research>
