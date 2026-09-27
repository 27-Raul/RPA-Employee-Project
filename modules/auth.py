import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

USERS = {
    'admin': {'password': 'admin123', 'role': 'HR Admin', 'name': 'HR Administrator'},
    'hr': {'password': 'hr123', 'role': 'HR Staff', 'name': 'HR Executive'},
    'manager': {'password': 'manager123', 'role': 'Manager', 'name': 'Department Manager'},
    'viewer': {'password': 'view123', 'role': 'Viewer', 'name': 'HR Viewer'}
}

def authenticate(username, password):
    """Authenticate a user."""
    logging.info(f"Attempting authentication for user: {username}")
    if username in USERS and USERS[username]['password'] == password:
        user_info = USERS[username].copy()
        user_info.pop('password')
        logging.info(f"Authentication successful for user: {username}")
        return {'success': True, 'user': user_info, 'error': None}
    
    logging.warning(f"Authentication failed for user: {username}")
    return {'success': False, 'user': None, 'error': 'Invalid username or password'}

def get_user_permissions(role):
    """Return permissions based on role."""
    permissions = {
        'can_register': False,
        'can_view_salary': False,
        'can_delete': False,
        'can_generate_report': False,
        'can_upload_docs': False,
        'can_approve': False
    }
    
    if role == 'HR Admin':
        for key in permissions:
            permissions[key] = True
    elif role == 'HR Staff':
        permissions['can_register'] = True
        permissions['can_view_salary'] = True
        permissions['can_upload_docs'] = True
    elif role == 'Manager':
        permissions['can_approve'] = True
    elif role == 'Viewer':
        pass # All false
        
    return permissions

def check_permission(role, action):
    """Check if a role has a specific permission."""
    perms = get_user_permissions(role)
    return perms.get(action, False)
