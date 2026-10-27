"""Self-tests for apply rule parsing and step-file generation."""

from apply import check_versions, run
from apply_constants import RULES_FILE
from file_io import read_text, save_json, write_text
from pathlib import Path
from project_setup import install_delegate_wrappers
from rule_blocks import (
    block_is_tailored, parse_block_version, parse_managed, parse_source_version_title,
    process_rules, reconcile_manifest,
)
import tempfile
import step_rules


def self_test():
    generated_plugin = Path(tempfile.mkdtemp())
    generated_rules = generated_plugin / "rules"
    generated_rules.mkdir()
    generated_source = generated_rules / "SAMPLE.md"
    generated_source.write_text(
        "# Version\n1\n\n# Sample Rules\n\nshared\n\n"
        "## Code only\n<!-- steps: code -->\ncode detail\n", encoding="utf-8")
    save_json(generated_rules / "versions.json", {"pointer": 3, "SAMPLE.md": 1})
    generated_project = Path(tempfile.mkdtemp())
    generated_report = run(
        generated_project, generated_plugin, ["SAMPLE.md"], "neither"
    )
    expected_step_files = list(step_rules.STEP_FILES.values())
    assert generated_report["step_files"] == expected_step_files, generated_report
    complete_rules = read_text(generated_project / RULES_FILE)
    assert "code detail" in complete_rules and (
        "instructions name one of these step files" in read_text(
            generated_project / "CLAUDE.md"
        )
    )
    plan_rules = read_text(generated_project / step_rules.STEP_FILES["plan"])
    assert "shared" in plan_rules and "code detail" not in plan_rules, plan_rules
    for filename in expected_step_files:
        assert parse_block_version(
            read_text(generated_project / filename)
        ) == 1, filename

    generated_source.write_text(
        "# Version\n2\n\n# Sample Rules\n\nshared v2\n\n"
        "## Code only\n<!-- steps: code -->\ncode detail v2\n", encoding="utf-8")
    save_json(generated_rules / "versions.json", {"pointer": 3, "SAMPLE.md": 2})
    run(generated_project, generated_plugin, ["SAMPLE.md"], "neither")
    assert parse_block_version(read_text(generated_project / RULES_FILE)) == 2
    assert all(parse_block_version(read_text(generated_project / filename)) == 2
               for filename in expected_step_files)

    empty_project = Path(tempfile.mkdtemp())
    for filename in expected_step_files:
        write_text(empty_project / filename, "stale step rules")
    empty_report = run(empty_project, generated_plugin, [], "neither")
    assert empty_report["step_files"] == [] and all(
        not (empty_project / filename).exists() for filename in expected_step_files)

    invalid_plugin = Path(tempfile.mkdtemp())
    (invalid_plugin / "rules").mkdir()
    (invalid_plugin / "rules" / "BAD.md").write_text(
        "# Version\n1\n\n# Bad\n<!-- steps: code, someday -->\n", encoding="utf-8")
    save_json(invalid_plugin / "rules" / "versions.json", {"BAD.md": 1})
    try:
        check_versions(invalid_plugin)
        raise AssertionError("unknown step marker must fail check-versions")
    except SystemExit as exc:
        assert exc.code == 1

    # Delegate wrappers are installed by the shared apply boundary and only
    # rewritten when their shipped content changes.
    wrapper_root = Path(tempfile.mkdtemp())
    wrapper_plugin = Path(tempfile.mkdtemp())
    wrapper_sources = wrapper_plugin / "rules" / "delegate_setup_files"
    wrapper_sources.mkdir(parents=True)
    for name, content in (("coding_rules_delegate.sh", "shell v1\n"),
                          ("coding_rules_delegate.ps1", "powershell v1\n")):
        (wrapper_sources / name).write_text(content, encoding="utf-8")
    assert install_delegate_wrappers(wrapper_root, wrapper_plugin)
    installed = wrapper_root / "tools" / "coding_rules_delegate.sh"
    assert read_text(installed) == "shell v1\n"
    installed_mtime = installed.stat().st_mtime_ns
    assert not install_delegate_wrappers(wrapper_root, wrapper_plugin)
    assert installed.stat().st_mtime_ns == installed_mtime
    (wrapper_sources / "coding_rules_delegate.sh").write_text(
        "shell v2\n", encoding="utf-8"
    )
    assert install_delegate_wrappers(wrapper_root, wrapper_plugin)
    assert read_text(installed) == "shell v2\n"
    # parse_source_version_title
    v, t = parse_source_version_title("# Version\n3\n\ntext\n\n# My Title\n\nbody\n")
    assert (v, t) == (3, "# My Title"), (v, t)

    # fence-aware block splitting: an embedded example must not start a new block
    sample = (
        "# Version\n1\n\n# Real Title\n\nSee example:\n\n"
        "```markdown\n# Version\n1\n```\n\nmore body\n"
    )
    _, blocks = parse_managed(sample)
    assert len(blocks) == 1, blocks
    assert blocks[0]["title"] == "# Real Title", blocks[0]
    # process_rules: absent -> update, equal -> unchanged, manifest>source -> conflict
    src_dir = Path(tempfile.mkdtemp()) / "rules"
    src_dir.mkdir(parents=True)
    (src_dir / "FOO.md").write_text(
        "# Version\n2\n\n# Foo Rules\n\nbody\n", encoding="utf-8"
    )
    blocks, manifest_rules, report = process_rules(
        [], src_dir.parent, ["FOO.md"], {}, {}
    )
    assert report[0]["status"] == "updated" and manifest_rules["FOO.md"] == 2, report
    blocks, manifest_rules, report = process_rules(
        blocks, src_dir.parent, ["FOO.md"], manifest_rules, {}
    )
    assert report[0]["status"] == "unchanged", report
    blocks, manifest_rules, report = process_rules(
        blocks, src_dir.parent, ["FOO.md"], {"FOO.md": 5}, {}
    )
    assert report[0]["status"] == "conflict", report
    # tolerant version parse: historical blank-line format (regression: bug that
    # silently overwrote a v4 block with v3 source because int('') threw)
    assert parse_block_version("# Version\n\n4\n\n# Foo Rules\nbody\n") == 4
    assert parse_block_version("# Version\n2\n\n# Foo Rules\n") == 2
    assert parse_block_version("# Version\n\n# Foo Rules\n") is None
    # pre-manifest blocks in the blank-line format: conflict + unchanged paths
    blank_conflict = {
        "title": "# Foo Rules",
        "text": "# Version\n\n4\n\n# Foo Rules\n\nbody\n",
    }
    _, _, rep_bc = process_rules([blank_conflict], src_dir.parent, ["FOO.md"], {}, {})
    assert rep_bc[0]["status"] == "conflict", rep_bc
    blank_equal = {
        "title": "# Foo Rules",
        "text": "# Version\n\n2\n\n# Foo Rules\n\nbody\n",
    }
    _, _, rep_be = process_rules([blank_equal], src_dir.parent, ["FOO.md"], {}, {})
    assert rep_be[0]["status"] == "unchanged", rep_be

    # orphan tail preserved on replace (regression: user-authored sections after
    # the last managed block were deleted by a block update)
    stale_with_tail = {
        "title": "# Foo Rules",
        "text": (
            "# Version\n1\n\n# Foo Rules\n\nold body\n\n"
            "# My Project Notes\n\nkeep me\n"
        ),
    }
    blocks_o = [stale_with_tail]
    blocks_o, _, rep_o = process_rules(
        blocks_o, src_dir.parent, ["FOO.md"], {"FOO.md": 1}, {}
    )
    assert (
        rep_o[0]["status"] == "updated"
        and rep_o[0]["preserved"] == ["# My Project Notes"]
    ), rep_o
    assert len(blocks_o) == 2 and "keep me" in blocks_o[1]["text"], blocks_o
    assert "My Project Notes" not in blocks_o[0]["text"], blocks_o

    # multi-heading source (PYTHON/FLUTTER style): its own extra heading must
    # NOT be split out as an orphan
    (src_dir / "MULTI.md").write_text(
        "# Version\n1\n\n# Multi Rules\n\nbody\n\n# Essential Extras\n\nmore\n",
        encoding="utf-8",
    )
    old_multi = {
        "title": "# Multi Rules",
        "text": (
            "# Version\n0\n\n# Multi Rules\n\nold\n\n"
            "# Essential Extras\n\nold more\n"
        ),
    }
    blocks_m = [old_multi]
    blocks_m, _, rep_m = process_rules(blocks_m, src_dir.parent, ["MULTI.md"], {}, {})
    assert rep_m[0]["status"] == "updated" and "preserved" not in rep_m[0], rep_m
    assert len(blocks_m) == 1 and "old more" not in blocks_m[0]["text"], blocks_m

    # tailored marker: stale -> tailored-stale + untouched; equal -> unchanged
    tailored_stale = {
        "title": "# Foo Rules",
        "text": "# Version\n1\n\n# Foo Rules\n<!-- tailored -->\n\ncustom body\n",
    }
    _, mf_ts, rep_ts = process_rules(
        [tailored_stale], src_dir.parent, ["FOO.md"], {}, {}
    )
    assert rep_ts[0]["status"] == "tailored-stale", rep_ts
    assert "custom body" in tailored_stale["text"]
    assert mf_ts["FOO.md"] == 1, mf_ts
    tailored_equal = {
        "title": "# Foo Rules",
        "text": "# Version\n2\n\n# Foo Rules\n<!-- tailored -->\n\ncustom body\n",
    }
    _, mf_te, rep_te = process_rules(
        [tailored_equal], src_dir.parent, ["FOO.md"], {}, {}
    )
    assert rep_te[0]["status"] == "unchanged" and mf_te["FOO.md"] == 2, rep_te
    # a fenced '<!-- tailored -->' (documentation example) does not count
    assert not block_is_tailored("# Version\n1\n\n# X\n\n```\n<!-- tailored -->\n```\n")

    # process_rules: pre-manifest project -- existing block already at current
    # version must NOT be rewritten just because the manifest has no entry,
    # AND (regression for the real bug) it must still land in the manifest
    # even though its "unchanged" status never touched the on-disk block.
    preexisting_block = {
        "title": "# Foo Rules",
        "text": "# Version\n2\n\n# Foo Rules\n\nbody\n",
    }
    _, manifest_premanifest, report_premanifest = process_rules(
        [preexisting_block], src_dir.parent, ["FOO.md"], {}, {})
    assert report_premanifest[0]["status"] == "unchanged", report_premanifest
    assert manifest_premanifest == {"FOO.md": 2}, manifest_premanifest

    # process_rules: a conflicting rule must also stay on record, not vanish
    _, manifest_conflict, report_conflict = process_rules(
        [preexisting_block], src_dir.parent, ["FOO.md"], {"FOO.md": 9}, {})
    assert report_conflict[0]["status"] == "conflict", report_conflict
    assert manifest_conflict == {"FOO.md": 9}, manifest_conflict

    # reconcile_manifest: a block already in CODING_RULES.md whose rel was
    # never passed in --rules (real-world cause: an earlier, pre-manifest
    # install) must still be recorded.
    other_block = {
        "title": "# Bar Rules",
        "text": "# Version\n4\n\n# Bar Rules\n\nbody\n",
    }
    reconciled = reconcile_manifest(
        [preexisting_block, other_block], {"FOO.md": 2},
        {"# Foo Rules": "FOO.md", "# Bar Rules": "BAR.md"}
    )
    assert reconciled == {"FOO.md": 2, "BAR.md": 4}, reconciled
    # already-recorded rels and unrecognized titles are left alone
    reconciled2 = reconcile_manifest(
        [preexisting_block], {"FOO.md": 99}, {"# Foo Rules": "FOO.md"}
    )
    assert reconciled2 == {"FOO.md": 99}, reconciled2
    # The block's own version must not clobber the recorded version.
    unrecognized_block = {
        "title": "# Untracked Section",
        "text": "# Version\n1\n\n# Untracked Section\n\nbody\n",
    }
    reconciled3 = reconcile_manifest([unrecognized_block], {}, {})
    assert reconciled3 == {}, reconciled3

