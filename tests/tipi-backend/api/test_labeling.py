import pytest

from tipi_backend.settings import Config

FIXTURE_DIR = "tests/tipi-backend/api/scanner_text/"


@pytest.fixture
def sync_word_limit():
    """Override TAGGER_MAX_WORDS so all scanner_text fixtures stay in the sync path."""
    original = Config.TAGGER_MAX_WORDS
    Config.TAGGER_MAX_WORDS = 5001
    yield
    Config.TAGGER_MAX_WORDS = original


@pytest.mark.parametrize("filename,expected_subset", [
    (
        "w100.txt",
        {
            "ODS 16 Paz, justicia e instituciones sólidas": ["Elusión y evasión fiscal"],
        },
    ),
    (
        "w500.txt",
        {
            "ODS 5 Igualdad de género": ["Aborto"],
            "ODS 6 Agua limpia y saneamiento": ["Contaminación del agua"],
        },
    ),
    (
        "w1000.txt",
        {
            "ODS 16 Paz, justicia e instituciones sólidas": ["Rendición de cuentas"],
            "ODS 5 Igualdad de género": ["Empoderamiento de las mujeres y las niñas"],
        },
    ),
    (
        "w2000.txt",
        {
            "ODS 7 Energía asequible y no contaminante": ["Transición energética"],
            "ODS 11 Ciudades y comunidades sostenibles": ["Electrificación de la movilidad"],
        },
    ),
    (
        "w5000.txt",
        {
            "ODS 17 Alianzas para lograr los objetivos": ["Remesas"],
            "ODS 5 Igualdad de género": ["Natalidad"],
            "ODS 8 Trabajo decente y crecimiento económico": ["Desempleo"],
        },
    ),
])
def test_extract_tags(client, sync_word_limit, filename, expected_subset):
    with open(FIXTURE_DIR + filename, "r") as f:
        text = f.read()

    res = client.post("/tagger/", data={"text": text})
    assert res.status_code == 200

    body = res.json()
    assert body["status"] == "SUCCESS"
    assert "result" in body

    result = body["result"]
    topics = result["topics"]
    tags = result["tags"]
    assert len(topics) > 0, f"{filename}: expected at least one topic"
    assert len(tags) > 0, f"{filename}: expected at least one tag"

    # Verify tag schema: required fields present, 'public' removed by remove_fields
    returned_by_topic = {}
    for tag in tags:
        assert "topic" in tag
        assert "subtopic" in tag
        assert "tag" in tag
        assert "knowledgebase" in tag
        assert "times" in tag
        assert "public" not in tag, "remove_fields should have deleted 'public'"
        assert tag["topic"] in topics, f"tag topic '{tag['topic']}' missing from topics list"
        returned_by_topic.setdefault(tag["topic"], []).append(tag["tag"])

    # Known-subset: a small set of high-confidence topic/tag pairs per fixture
    for topic, expected_tags in expected_subset.items():
        assert topic in topics, f"{filename}: expected topic '{topic}'"
        for expected_tag in expected_tags:
            assert expected_tag in returned_by_topic.get(topic, []), (
                f"{filename}: expected tag '{expected_tag}' under topic '{topic}'"
            )


def test_async_dispatch(client):
    """Texts >= TAGGER_MAX_WORDS are dispatched asynchronously."""
    original = Config.TAGGER_MAX_WORDS
    Config.TAGGER_MAX_WORDS = 10
    try:
        res = client.post("/tagger/", data={"text": "word " * 11})
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "PROCESSING"
        assert "task_id" in body
        assert "estimated_time" in body
    finally:
        Config.TAGGER_MAX_WORDS = original
