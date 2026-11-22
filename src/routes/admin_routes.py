from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from src.models.model_registry_model import ModelRegistry
from src.models.audit_log_model import AuditLog
from src.security.permissions import roles_required, ROLE_ADMIN

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/')
@admin_bp.route('/settings')
@login_required
@roles_required(ROLE_ADMIN)
def admin_settings():
    """System administration & ML model governance portal."""
    models = ModelRegistry.query.all()
    audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(50).all()

    return render_template(
        'admin_settings.html',
        models=models,
        audit_logs=audit_logs
    )

@admin_bp.route('/api/models/<model_id>', methods=['GET'])
@login_required
@roles_required(ROLE_ADMIN)
def get_model_details(model_id):
    """API endpoint providing comprehensive model governance specifications."""
    models_data = {
        'model_01': {
            'model_id': 'model_01',
            'model_identifier': 'order_creation-v1.0.0',
            'name': 'Model-01: Order Creation Classifier',
            'algorithm': 'Logistic Regression / XGBoost',
            'stage': 'Order Creation (Pre-dispatch)',
            'role': 'Primary Classifier',
            'status': 'Active Production (v1.0)',
            'features_count': 18,
            'features_scope': '18 Commercial & Scheduled Lane Features (No Actual Transit Leakage)',
            'target_leakage_protected': True,
            'optimal_threshold': 0.40,
            'metrics': {
                'accuracy': 0.6812,
                'precision': 0.6983,
                'recall': 0.7404,
                'f1': 0.7187,
                'roc_auc': 0.7593,
                'pr_auc': 0.8228,
                'brier': 0.1871
            }
        },
        'model_02': {
            'model_id': 'model_02',
            'model_identifier': 'dispatch_stage-v1.2.0',
            'name': 'Model-02: Dispatch Stage Predictor',
            'algorithm': 'XGBoost Classifier',
            'stage': 'Dispatch & Quay Release',
            'role': 'Secondary Triage',
            'status': 'Active Production (v1.2)',
            'features_scope': 'Order-to-Ship Lag, Warehouse Dwell, Seaport Routing',
            'optimal_threshold': 0.39,
            'metrics': {
                'accuracy': 0.9752,
                'precision': 1.0,
                'recall': 0.9507,
                'f1': 0.9747,
                'roc_auc': 0.9986,
                'brier': 0.0221
            }
        },
        'model_03': {
            'model_id': 'model_03',
            'model_identifier': 'delay_duration-v1.1.0',
            'name': 'Model-03: Delay Duration Estimator',
            'algorithm': 'CatBoost Regressor',
            'stage': 'Post-Flagging Delay Sizing',
            'role': 'Hours Estimation',
            'status': 'Active Production (v1.1)',
            'features_scope': 'Vessel Class, Distance Matrix, Historical Maritime Dwell',
            'metrics': {
                'mae_days': 0.34,
                'r2_score': 0.894
            }
        }
    }

    if model_id in models_data:
        return jsonify(models_data[model_id])
    return jsonify({'error': 'Model not found'}), 404

@admin_bp.route('/thresholds', methods=['POST'])
@login_required
@roles_required(ROLE_ADMIN)
def update_thresholds():
    """Update global prediction decision threshold."""
    data = request.get_json(silent=True) or request.form
    new_threshold = float(data.get('threshold', 0.40))

    audit = AuditLog(
        user_id=current_user.id,
        action='MODEL_THRESHOLD_UPDATED',
        entity='SETTINGS',
        entity_id='GLOBAL_THRESHOLD',
        details=f"Decision threshold updated to {new_threshold}"
    )
    db.session.add(audit)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'threshold': new_threshold})
    flash(f'Decision threshold updated to {new_threshold}.', 'success')
    return redirect(url_for('admin_bp.admin_settings'))
