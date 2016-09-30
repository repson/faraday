# Faraday Penetration Test IDE
# Copyright (C) 2016  Infobyte LLC (http://www.infobytesec.com/)
# See the file 'doc/LICENSE' for the license information

import flask
import json

from server.app import app
from server.dao.host import HostDAO
from server.dao.vuln import VulnerabilityDAO
from server.dao.service import ServiceDAO
from server.dao.interface import InterfaceDAO
from server.dao.note import NoteDAO
from server.utils.web import gzipped, validate_workspace, get_basic_auth, validate_admin_perm, validate_database, build_bad_request_response
from server.couchdb import list_workspaces_as_user, get_workspace, get_auth_info
from server.database import get_manager


@app.route('/ws', methods=['GET'])
@gzipped
def workspace_list():
    return flask.jsonify(
        list_workspaces_as_user(
            flask.request.cookies, get_basic_auth()))

@app.route('/ws/<workspace>/summary', methods=['GET'])
@gzipped
def workspace_summary(workspace=None):
    validate_workspace(workspace)

    services_count = ServiceDAO(workspace).count()
    vuln_count = VulnerabilityDAO(workspace).count(vuln_filter=flask.request.args)
    host_count = HostDAO(workspace).count()
    iface_count = InterfaceDAO(workspace).count()
    note_count = NoteDAO(workspace).count()

    response = {
        'stats': {
            'services':    services_count.get('total_count', 0),
            'total_vulns': vuln_count.get('total_count', 0),
            'web_vulns':   vuln_count.get('web_vuln_count', 0),
            'std_vulns':   vuln_count.get('vuln_count', 0),
            'hosts':       host_count.get('total_count', 0),
            'interfaces':  iface_count.get('total_count', 0),
            'notes':       note_count.get('total_count', 0),
        }
    }

    return flask.jsonify(response)

@app.route('/ws/<workspace>', methods=['GET'])
@gzipped
def workspace(workspace):
    validate_workspace(workspace)
    workspaces = list_workspaces_as_user(
        flask.request.cookies, get_basic_auth())['workspaces']
    ws = get_workspace(workspace, flask.request.cookies, get_basic_auth()) if workspace in workspaces else None
    # TODO: When the workspace DAO is ready, we have to remove this next line
    if not ws.get('fdate'): ws['fdate'] = ws.get('duration').get('end')
    if not ws.get('description'): ws['description'] = ''
    return flask.jsonify(ws)

@app.route('/ws/<workspace>', methods=['PUT'])
@gzipped
def workspace_create(workspace):
    # only admins can create workspaces
    validate_admin_perm()
    validate_database(workspace)

    try:
        document = json.loads(flask.request.data)
    except ValueError:
        return build_bad_request_response('invalid json')
    if not document.get('name', None):
        return build_bad_request_response('workspace name needed')
    if document.get('name') != workspace:
        return build_bad_request_response('workspace name and route parameter don\'t match')

    db_manager = get_manager()

    document['_id'] = workspace  # document dictionary does not have id, add it

    if not db_manager.create_workspace(document):
        response = flask.jsonify({'error': "There was an error creating the database"})
        response.status_code = 500
        return response

    return flask.jsonify({'ok': True})
