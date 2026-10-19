# Existing Docling runtime and bundled artifacts are fixed by digest. No model fetches.
FROM quay.io/docling-project/docling-serve@sha256:70ea35b4a94a27babd83d0ec8fc3ed8b0cd3ff3651595070edd15cea2ad9babf
USER 0
RUN mkdir -p /run/asila-parser && chown 1000:1000 /run/asila-parser && chmod 770 /run/asila-parser
COPY backend/document_processing /opt/asila/document_processing
ENV HOME=/tmp MPLCONFIGDIR=/tmp/matplotlib PYTHONPATH=/opt/asila HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
USER 1000:1000
ENTRYPOINT ["python", "-m", "uvicorn", "document_processing.server:app", "--uds", "/run/asila-parser/parser.sock", "--no-access-log", "--log-level", "warning"]
