from flask import Blueprint, request, jsonify
from forensics.parser import parse_session
from forensics.annotator import annotate_session
from forensics.analyzer import analyze_session, AnalyzerConfig
from forensics.report import generate_report
from auth import check_auth

forensics_bp = Blueprint('forensics', __name__)

@forensics_bp.route('/forensics/analyze', methods=['POST'])
def analyze():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json(silent=True)
    if not data or 'jsonl' not in data:
        return jsonify({"error": "Missing 'jsonl' field in request body"}), 400
    
    jsonl_string = data['jsonl']
    session_id_override = data.get('session_id')
    
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
