from app.services.batch_concurrency import (
    cancel_all_background_batches,
    get_active_batch_metrics,
    get_global_job_semaphore,
    is_batch_running,
    stop_background_batch,
)
from app.services.batch_runner import (
    auto_resolve_batch_and_refill,
    launch_background_batch,
    refill_batch_deficit,
    retry_incomplete_jobs_for_batch,
)
from app.services.deduplication import (
    cluster_questions,
    evaluate_duplicate,
    evaluate_duplicate_rag,
)
from app.services.embeddings import (
    deterministic_unit_vector,
    embed_passage,
    embed_question,
    embed_text,
)
from app.services.rag import (
    RAGExemplarContext,
    SimilarQuestionResult,
    backfill_question_embeddings,
    find_similar_questions,
    hybrid_search_questions,
    retrieve_rag_exemplar_context,
)
from app.services.syllabus_ingestion import (
    SyllabusIngestionResult,
    extract_text_from_file_bytes,
    ingest_and_map_syllabus,
)

__all__ = [
    "RAGExemplarContext",
    "SimilarQuestionResult",
    "SyllabusIngestionResult",
    "auto_resolve_batch_and_refill",
    "backfill_question_embeddings",
    "cancel_all_background_batches",
    "cluster_questions",
    "deterministic_unit_vector",
    "embed_passage",
    "embed_question",
    "embed_text",
    "evaluate_duplicate",
    "evaluate_duplicate_rag",
    "extract_text_from_file_bytes",
    "find_similar_questions",
    "get_active_batch_metrics",
    "get_global_job_semaphore",
    "hybrid_search_questions",
    "ingest_and_map_syllabus",
    "is_batch_running",
    "launch_background_batch",
    "refill_batch_deficit",
    "retrieve_rag_exemplar_context",
    "retry_incomplete_jobs_for_batch",
    "stop_background_batch",
]
