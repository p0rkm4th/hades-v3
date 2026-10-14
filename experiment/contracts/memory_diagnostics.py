"""Privacy-safe correction diagnostics for isolated experiment instrumentation."""


def json_shape(value, depth=0):
    """Return a bounded structural description without values or object keys."""
    if depth >= 4:
        return "nested"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        child_shapes = sorted({json_shape(item, depth + 1) for item in value[:8]})
        return f"array:{len(value)}:[{','.join(child_shapes)}]"
    if isinstance(value, dict):
        child_shapes = sorted({json_shape(item, depth + 1) for item in list(value.values())[:8]})
        return f"object:{len(value)}:[{','.join(child_shapes)}]"
    return "unsupported"


def correction_diagnostic_class(query_matches, expected_matches, intersection_matches):
    """Classify a scoped correction mismatch without exposing record contents."""
    if intersection_matches == 1:
        return "unique_match"
    if intersection_matches > 1:
        return "ambiguous_intersection"
    if query_matches == 0:
        return "query_no_match"
    if expected_matches == 0:
        return "expected_value_no_match"
    if query_matches > 0 and expected_matches > 0:
        return "query_and_value_match_different_rows"
    return "unclassified_no_match"
