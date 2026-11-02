import json

import pytest
from PIL import Image

pytest.importorskip("mcp")

from nuqta import mcp_server  # noqa: E402
from nuqta.ocr import Page, Result  # noqa: E402

MRZ = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\nL898902C36UTO7408122F1204159ZE184226B<<<<<10"


class FakeOCR:
    """Stands in for OCR: records each call, returns one numbered page per input."""

    def __init__(self, text="نص عربي"):
        self.text, self.calls = text, []

    def read_many(self, srcs, mode="as-written"):
        self.calls.append((srcs, mode))
        return [Result([Page(f"{self.text} {i + 1}")], mode) for i in range(len(srcs))]


@pytest.fixture
def fake(monkeypatch):
    f = FakeOCR()
    monkeypatch.setattr(mcp_server, "_ocr", f)
    return f


@pytest.fixture
def pdf(tmp_path):
    path = tmp_path / "doc.pdf"
    Image.new("RGB", (100, 140), "white").save(path, save_all=True,
                                               append_images=[Image.new("RGB", (100, 140), "white")] * 2)
    return path


def test_reads_an_image(fake, tmp_path):
    img = tmp_path / "page.png"
    Image.new("RGB", (64, 64), "white").save(img)
    assert mcp_server.read_document(str(img)) == "نص عربي 1"
    assert fake.calls == [([str(img)], "as-written")]


def test_pdf_pages(fake, pdf):
    out = mcp_server.read_document(str(pdf), mode="bare", pages="1,3")
    assert out == "--- page 1 ---\nنص عربي 1\n\n--- page 3 ---\nنص عربي 2"
    srcs, mode = fake.calls[0]
    assert mode == "bare" and len(srcs) == 2 and all(isinstance(s, Image.Image) for s in srcs)
    assert "--- page 2 ---" in mcp_server.read_document(str(pdf))


def test_id_mode_appends_fields(monkeypatch, tmp_path):
    monkeypatch.setattr(mcp_server, "_ocr", FakeOCR("PASSPORT\n" + MRZ))
    img = tmp_path / "passport.jpg"
    Image.new("RGB", (64, 64), "white").save(img)
    out = mcp_server.read_document(str(img), mode="id")
    fields = json.loads(out.split("```json\n")[1].split("\n```")[0])
    assert fields["mrz"]["number"] == "L898902C3" and fields["mrz"]["valid"]


@pytest.mark.parametrize("path, mode, pages, msg", [
    ("/no/such/file.png", "as-written", None, "file not found"),
    ("relative.png", "as-written", None, "must be absolute"),
    ("/", "as-written", None, "not a file"),
    ("{pdf}", "fancy", None, "mode must be one of"),
    ("{pdf}", "as-written", "4", "out of range"),
    ("{pdf}", "as-written", "x-y", "must look like"),
])
def test_errors(fake, pdf, path, mode, pages, msg):
    with pytest.raises(mcp_server.ToolError, match=msg):
        mcp_server.read_document(path.format(pdf=pdf), mode=mode, pages=pages)
    assert not fake.calls


def test_unreadable_image(fake, tmp_path):
    bad = tmp_path / "bad.png"
    bad.write_text("not an image")
    fake.read_many = lambda srcs, mode: Image.open(srcs[0])  # what load_image does with a broken file
    with pytest.raises(mcp_server.ToolError, match="cannot read bad.png"):
        mcp_server.read_document(str(bad))


def test_tool_is_listed_over_mcp(fake, tmp_path):
    import anyio

    try:
        from mcp import Client
    except ImportError:
        pytest.skip("the in-process Client needs mcp 2")

    img = tmp_path / "page.png"
    Image.new("RGB", (64, 64), "white").save(img)

    async def go():
        async with Client(mcp_server.server) as c:
            tools = (await c.list_tools()).tools
            res = await c.call_tool("read_document", {"path": str(img)})
            return tools, res

    tools, res = anyio.run(go)
    assert [t.name for t in tools] == ["read_document"]
    assert "tashkeel" in tools[0].description.lower() and "markdown" in tools[0].description
    assert not res.is_error and res.content[0].text == "نص عربي 1"
