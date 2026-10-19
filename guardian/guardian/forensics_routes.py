from flask import Blueprint, jsonify, request

from guardian.forensics.analyzer import AnalyzerConfig, analyze_session
from guardian.forensics.annotator import annotate_session
from guardian.forensics.parser import parse_session
from guardian.forensics.report import generate_report
from guardian.guardian.auth import check_auth

forensics_bp = Blueprint("forensics", __name__)


@forensics_bp.route("/forensics/analyze", methods=["POST"])
def analyze():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "jsonl" not in data:
        return jsonify({"error": "Missing 'jsonl' field in request body"}), 400

    jsonl_string = data["jsonl"]
    session_id_override = data.get("session_id")
    if (
        not isinstance(jsonl_string, str)
        or len(jsonl_string) > 1024 * 1024
        or jsonl_string.count("\n") > 500
    ):
        return jsonify({"error": "Bounded JSONL string required"}), 400
    if session_id_override is not None and (
        not isinstance(session_id_override, str) or len(session_id_override) > 128
    ):
        return jsonify({"error": "Invalid session_id"}), 400

    try:
        # 1. Parse
        session = parse_session(jsonl_string, is_file=False)
        if session_id_override:
            session.session_id = session_id_override

        # 2. Annotate
        annotated = annotate_session(session)

        # 3. Analyze
        config = AnalyzerConfig()
        behavior_report = analyze_session(annotated, config)

        # 4. Report
        final_report = generate_report(behavior_report, annotated)

        return jsonify(final_report.to_dict()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
