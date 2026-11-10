import json
import os

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import ChatMessage, Document
from .services import ingestion, ollama_client, retrieval, vectorstore
from .services.ollama_client import OllamaError


def _doc(d):
    return {"id": d.id, "name": d.name, "type": d.file_type, "chunks": d.chunk_count,
            "status": d.status, "error": d.error, "created_at": d.created_at.isoformat()}


@csrf_exempt
@require_http_methods(["GET", "POST"])
def documents(request):
    if request.method == "GET":
        return JsonResponse({"documents": [_doc(d) for d in Document.objects.all()]})

    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "Attach a file in the 'file' field."}, status=400)
    ext = os.path.splitext(f.name)[1].lower().lstrip(".")
    if ext not in ingestion.SUPPORTED:
        return JsonResponse({"error": f"Unsupported type. Use: {', '.join(sorted(ingestion.SUPPORTED))}."}, status=400)
    if f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        return JsonResponse({"error": f"File exceeds {settings.MAX_UPLOAD_MB} MB."}, status=413)

    doc = Document.objects.create(name=f.name, file=f, file_type=ext)
    try:
        ingestion.ingest(doc)
    except OllamaError as exc:
        return JsonResponse({"error": f"Ollama unavailable: {exc}"}, status=502)
    except Exception as exc:
        return JsonResponse({"error": f"Could not process file: {exc}"}, status=422)
    return JsonResponse(_doc(doc), status=201)


@csrf_exempt
@require_http_methods(["DELETE"])
def document_detail(request, pk):
    try:
        doc = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return JsonResponse({"error": "Document not found."}, status=404)
    vectorstore.delete_document(doc.id)
    doc.file.delete(save=False)
    doc.delete()
    return JsonResponse({"deleted": pk})


@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    try:
        body = json.loads(request.body or "{}")
        question = (body.get("question") or "").strip()
        top_k = min(max(int(body.get("top_k") or settings.TOP_K), 1), 10)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    if not question:
        return JsonResponse({"error": "'question' is required."}, status=400)
    try:
        result = retrieval.answer(question, top_k)
    except OllamaError as exc:
        return JsonResponse({"error": f"Ollama unavailable: {exc}"}, status=502)
    ChatMessage.objects.create(question=question, answer=result["answer"], sources=json.dumps(result["sources"]))
    return JsonResponse(result)


@require_http_methods(["GET"])
def history(request):
    rows = ChatMessage.objects.order_by("-created_at")[:50][::-1]
    return JsonResponse({"messages": [
        {"question": m.question, "answer": m.answer, "sources": json.loads(m.sources)} for m in rows
    ]})


@require_http_methods(["GET"])
def health(request):
    try:
        available = ollama_client.models()
    except OllamaError as exc:
        return JsonResponse({"ollama": False, "error": str(exc)}, status=503)
    return JsonResponse({"ollama": True, "llm": settings.LLM_MODEL, "embed": settings.EMBED_MODEL,
                         "models_installed": available})
