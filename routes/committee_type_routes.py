from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from services_init import db, auth_manager, committee_types_service, audit_logger
from auth import editor_required
from services.committee_types_service import CommitteeTypeRequest

committee_type_bp = Blueprint('committee_types', __name__)

@committee_type_bp.route('/committee_types')
@editor_required
def committee_types():
    """Manage committee types"""
    # Get hativa_id from query parameters
    hativa_id = request.args.get('hativa_id', type=int)
    
    # Get committee types with statistics (filtered by division if specified)
    response = committee_types_service.get_committee_types_with_statistics(hativa_id)
    
    # Get all hativot for the dropdown
    hativot = db.get_hativot()
    
    if not response.success:
        flash(response.message, 'error')
    
    # Get current user info
    current_user = auth_manager.get_current_user()
    
    return render_template('committee_types.html', 
                         committee_types=response.committee_types,
                         weekly_count=response.statistics['weekly_count'],
                         monthly_count=response.statistics['monthly_count'],
                         active_meetings_count=response.statistics['active_meetings_count'],
                         hativot=hativot,
                         current_user=current_user,
                         selected_hativa_id=hativa_id)

@committee_type_bp.route('/committee_types/add', methods=['POST'])
@editor_required
def add_committee_type():
    """Add new committee type"""
    # Create request object from form data
    committee_type_request = CommitteeTypeRequest(
        hativa_id=request.form.get('hativa_id', type=int),
        name=request.form.get('name', '').strip(),
        scheduled_day=request.form.get('scheduled_day', type=int),
        frequency=request.form.get('frequency', '').strip(),
        week_of_month=request.form.get('week_of_month', type=int) if request.form.get('week_of_month') else None,
        description=request.form.get('description', '').strip(),
        is_operational=1 if request.form.get('is_operational') in ('1', 'on', 'true', 'True') else 0
    )
    
    # Use service to create committee type
    response = committee_types_service.create_committee_type(committee_type_request)
    
    # Log the operation
    if response.success and response.committee_type_id:
        hativot = db.get_hativot()
        hativa = next((h for h in hativot if h['hativa_id'] == committee_type_request.hativa_id), None)
        hativa_name = hativa['name'] if hativa else 'Unknown'
        audit_logger.log_committee_type_created(
            response.committee_type_id,
            committee_type_request.name,
            hativa_name
        )
    elif not response.success:
        audit_logger.log_error(
            audit_logger.ACTION_CREATE,
            audit_logger.ENTITY_COMMITTEE_TYPE,
            response.message,
            entity_name=committee_type_request.name
        )
    
    # Flash appropriate message
    flash(response.message, 'success' if response.success else 'error')
    
    return redirect(url_for('committee_types.committee_types'))

@committee_type_bp.route('/committee_types/update', methods=['POST'])
@editor_required
def update_committee_type():
    """Update existing committee type"""
    committee_type_id = request.form.get('committee_type_id', type=int)
    
    # Create request object from form data
    committee_type_request = CommitteeTypeRequest(
        hativa_id=request.form.get('hativa_id', type=int),
        name=request.form.get('name', '').strip(),
        scheduled_day=request.form.get('scheduled_day', type=int),
        frequency=request.form.get('frequency', '').strip(),
        week_of_month=request.form.get('week_of_month', type=int) if request.form.get('week_of_month') else None,
        description=request.form.get('description', '').strip(),
        is_operational=1 if request.form.get('is_operational') in ('1', 'on', 'true', 'True') else 0
    )
    
    # Use service to update committee type
    response = committee_types_service.update_committee_type(committee_type_id, committee_type_request)
    
    # Log the operation
    if response.success:
        audit_logger.log_committee_type_updated(committee_type_id, committee_type_request.name)
    else:
        audit_logger.log_error(
            audit_logger.ACTION_UPDATE,
            audit_logger.ENTITY_COMMITTEE_TYPE,
            response.message,
            committee_type_id,
            committee_type_request.name
        )
    
    # Flash appropriate message
    flash(response.message, 'success' if response.success else 'error')
    
    return redirect(url_for('committee_types.committee_types'))

@committee_type_bp.route('/committee_types/delete', methods=['POST'])
@editor_required
def delete_committee_type():
    """Delete committee type"""
    committee_type_id = request.form.get('committee_type_id', type=int)
    
    # Get committee type name before deletion
    committee_types_list = db.get_committee_types()
    committee_type = next((ct for ct in committee_types_list if ct['committee_type_id'] == committee_type_id), None)
    ct_name = committee_type['name'] if committee_type else 'Unknown'
    
    # Use service to delete committee type
    response = committee_types_service.delete_committee_type(committee_type_id)
    
    # Log the operation
    if response.success:
        audit_logger.log_committee_type_deleted(committee_type_id, ct_name)
    else:
        audit_logger.log_error(
            audit_logger.ACTION_DELETE,
            audit_logger.ENTITY_COMMITTEE_TYPE,
            response.message,
            committee_type_id,
            ct_name
        )
    
    # Flash appropriate message
    flash(response.message, 'success' if response.success else 'error')
    
    return redirect(url_for('committee_types.committee_types'))
