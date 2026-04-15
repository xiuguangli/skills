import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "render_survey.py"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("render_survey_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RENDER_MODULE = load_module()


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def render_cli(input_path: Path, output_path: Path) -> str:
    subprocess.run([sys.executable, str(SCRIPT_PATH), str(input_path), "-o", str(output_path)], check=True)
    return output_path.read_text(encoding="utf-8")


def test_render_v2_fixture_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "research_papers_v2.md"
    content = render_cli(FIXTURE_DIR / "research_papers_v2_minimal.json", output_path)

    assert "## 综合总结" in content
    assert "### Topic 演化时间线" in content
    assert "PDF：" in content
    assert "访问链接：" in content
    assert "证据等级：全文验证" in content
    assert "最低总保留论文数：200" in content
    assert "opens（开启主线）" in content
    assert "MapFusion for Embodied Spatial Intelligence" in content
    assert "](https://example.com/mapfusion-paper)" in content


def test_render_legacy_fixture_shows_warning_without_fabricated_timeline(tmp_path: Path) -> None:
    output_path = tmp_path / "research_papers_v1.md"
    content = render_cli(FIXTURE_DIR / "research_papers_v1_legacy.json", output_path)

    assert "## 兼容性提示" in content
    assert "legacy 1.x 兼容模式" in content
    assert "访问链接：" in content
    assert "证据等级：旧版未标注" in content
    assert "### Topic 演化时间线" in content
    assert "不会伪造代表论文关系" in content
    assert "opens（开启主线）" not in content


def test_render_blocked_warning_and_topic_metadata() -> None:
    data = copy.deepcopy(load_fixture("research_papers_v2_minimal.json"))
    data["selection_status"] = "blocked_insufficient_candidates"
    data["requirement_failures"] = ["最低总保留论文数 200 未满足，当前仅 127 篇。"]
    data["subtopics"][0]["allocation"] = {
        "target": 200,
        "selected": 127,
        "rebalance_delta": -73,
    }

    content = RENDER_MODULE.render(data)

    assert "## 结果告警" in content
    assert "blocked_insufficient_candidates" in content
    assert "最低总保留论文数 200 未满足，当前仅 127 篇。" in content
    assert "### Topic 配额与检索" in content
    assert "rebalance_delta=-73" in content
