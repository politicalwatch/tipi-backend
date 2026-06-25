import codecs
import logging
import pickle
import subprocess
import tempfile
from os.path import splitext
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from pptx import Presentation

import tipi_tasks
from tipi_backend.api import cache
from tipi_backend.api.business import get_tags, get_kbs
from tipi_backend.api.request_models import KbQuery
from tipi_backend.settings import Config


log = logging.getLogger(__name__)

router = APIRouter(prefix="/tagger", tags=["tagger"])


def filter_tags(result, kb):
    tags = result["result"]["tags"]
    new_topics = []
    new_tags = []
    for tag in tags:
        if tag["knowledgebase"] in kb:
            new_tags.append(tag)
            new_topics.append(tag["topic"])
    new_topics = list(set(new_topics))
    result["result"]["topics"] = new_topics
    result["result"]["tags"] = new_tags
    return result


def remove_fields(result):
    tags = result["result"]["tags"]
    for tag in tags:
        del tag["public"]


def _extract_text_from_file(file: UploadFile) -> str:
    with tempfile.NamedTemporaryFile(
        prefix="tipiscanner_", suffix=splitext(file.filename)[1]
    ) as f:
        f.write(file.file.read())
        f.seek(0)
        mimetype = file.content_type
        if mimetype == "text/plain":
            text = f.read().decode("utf-8").strip()
        elif mimetype == "application/pdf":
            text = extract_pdf_text(f.name).strip()
        elif mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(f)
            text = "\n".join([para.text for para in doc.paragraphs]).strip()
        elif mimetype == "application/msword":
            result = subprocess.run(
                ["antiword", f.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            if result.returncode != 0:
                raise Exception(
                    f"Error al leer el archivo .doc: {result.stderr.decode('utf-8')}"
                )
            text = result.stdout.decode("utf-8").strip()
        elif mimetype == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            ppt = Presentation(f)
            text = "\n".join(
                [
                    shape.text
                    for slide in ppt.slides
                    for shape in slide.shapes
                    if hasattr(shape, "text")
                ]
            ).strip()
        else:
            raise HTTPException(
                status_code=400,
                detail="Formato no soportado. Por favor, utilice un archivo .txt, .pdf, .docx, .doc o .pptx.",
            )
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Error al obtener el texto del fichero proporcionado. Pruebe con otro fichero.",
        )
    return text


@router.post("/")
def extract(
    text: Annotated[str, Form()] = "",
    file: Annotated[UploadFile | str | None, File()] = None,
    knowledgebase: Annotated[str, Form()] = "",
):
    """Returns a list of topics and tags matching the text."""
    try:
        # Blank knowledgebase = no filter (all public KBs), matching Flask's default.
        # The empty default also stops Swagger "Try it out" from sending `"string"`.
        kb = get_kbs({"knowledgebase": knowledgebase or None})

        cache_key = Config.CACHE_TAGS
        tags = cache.get(cache_key)
        if tags is None:
            tags = get_tags()
            cache.set(cache_key, tags, timeout=5 * 60)
        tags = codecs.encode(pickle.dumps(tags), "base64").decode()
        tipi_tasks.init()

        content = ""
        if text:
            content = text
        elif isinstance(file, UploadFile):
            content = _extract_text_from_file(file)

        text_length = len(content.split())

        if text_length >= Config.TAGGER_MAX_WORDS:
            task = tipi_tasks.tagger.extract_tags_from_text.apply_async((content, tags))
            eta_time = int((text_length / 1000) * 4)
            return {
                "status": "PROCESSING",
                "task_id": task.id,
                "estimated_time": eta_time,
            }

        result = tipi_tasks.tagger.extract_tags_from_text(content, tags)
        result = filter_tags(result, kb)
        remove_fields(result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/result/{id}")
def tagger_result(id: str, query: Annotated[KbQuery, Query()]):
    """Returns tagging task's result."""
    try:
        tipi_tasks.init()
        result = tipi_tasks.tagger.check_status_task(id)

        kb = get_kbs(query.model_dump())
        if result["status"] == "SUCCESS":
            result = filter_tags(result, kb)
            remove_fields(result)
        return result
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No task found"})
