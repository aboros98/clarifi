"""Clarifi tools — Python functions callable by the LLM via tool-calling."""

from clarifi.tools.alerts import query_alerts
from clarifi.tools.analysis import (
    detect_unissued_invoices,
    project_cashflow_daily,
    score_client_risk,
)
from clarifi.tools.calculator import calculate
from clarifi.tools.clarification import ask_user
from clarifi.tools.data_search import search_data
from clarifi.tools.discovery import discover_data
from clarifi.tools.cloud_sync import sync_google_drive, upload_to_storage
from clarifi.tools.contracts import query_contracts, query_milestones
from clarifi.tools.correlation import check_contract_status, reconcile_project
from clarifi.tools.data_queries import mark_invoice_paid, query_invoices, query_transactions
from clarifi.tools.documents import ingest_document, save_extracted_data
from clarifi.tools.extraction import extract_fields
from clarifi.tools.feedback import check_freshness, confirm_data, correct_data, mark_stale
from clarifi.tools.file_manager import (
    create_folder,
    get_file_tree,
    list_folders,
    move_file,
    read_document_content,
)
from clarifi.tools.finance import query_cashflow, query_profitability, query_receivables
from clarifi.tools.matching import confirm_match, run_payment_matching
from clarifi.tools.scheduling import cancel_reminder, create_reminder, list_reminders
from clarifi.tools.traces import read_trace, write_trace

ALL_TOOLS = [
    # Finance
    query_cashflow,
    query_receivables,
    query_profitability,
    # Data queries
    query_invoices,
    query_transactions,
    mark_invoice_paid,
    # Contracts
    query_contracts,
    query_milestones,
    # Correlation
    check_contract_status,
    reconcile_project,
    # Matching
    run_payment_matching,
    confirm_match,
    # Alerts & Analysis
    query_alerts,
    detect_unissued_invoices,
    project_cashflow_daily,
    score_client_risk,
    # Documents & Extraction
    ingest_document,
    save_extracted_data,
    extract_fields,
    # File Management
    create_folder,
    list_folders,
    move_file,
    read_document_content,
    get_file_tree,
    # Traces
    read_trace,
    write_trace,
    # Cloud Sync
    upload_to_storage,
    sync_google_drive,
    # Clarification
    ask_user,
    # Feedback
    confirm_data,
    correct_data,
    mark_stale,
    check_freshness,
    # Scheduling
    create_reminder,
    list_reminders,
    cancel_reminder,
    # Calculator
    calculate,
    # Discovery & Search
    discover_data,
    search_data,
]
