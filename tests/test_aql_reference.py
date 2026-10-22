"""Independent AQL table cross-check with an MIT-licensed reference."""

from tools.check_aql_reference import compare


def test_direct_aql_cells_match_independent_reference():
    result = compare()
    assert result["ok"] is True, result["direct_mismatches"]
    assert result["direct_cells_checked"] == 54
    assert result["source_commit"] == "ee12b8d3a720d394a5fdb9b750047462e5200a2d"


def test_arrow_cells_are_explicitly_accounted_for():
    result = compare()
    assert len(result["arrow_cells"]) == 42
    assert result["arrow_accept_mismatches"] == 6
    assert all(item["resolved_code"] for item in result["arrow_cells"])
    assert "arrow" in result["arrow_note"].lower()
