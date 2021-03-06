#!/usr/bin/env python
# -*- coding: utf-8 -*-

# LINC is an open source shared database and facial recognition
# system that allows for collaboration in wildlife monitoring.
# Copyright (C) 2016  Wildlifeguardians
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For more information or to contact visit linclion.org or email tech@linclion.org

from tornado.web import asynchronous
from tornado.gen import engine, coroutine, Task
from handlers.base import BaseHandler
from bson import ObjectId as ObjId
from lib.rolecheck import api_authenticated
from logging import info


class CVRequestsHandler(BaseHandler):
    """ A class that handles requests about CV indentification informartion """
    SUPPORTED_METHODS = ('GET', 'POST', 'PUT', 'DELETE')

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, req_id=None):
        if req_id:
            if req_id == 'list':
                objs = yield self.CVRequests.find().skip(self.skip).limit(self.limit).to_list(None)
                output = yield Task(self.list, objs)
                self.response(200, 'CV Requests list.', output)
            else:
                query = self.query_id(req_id)
                obj = yield self.CVRequests.find_one(query)
                if obj:
                    objreq = obj
                    objreq['id'] = obj['iid']
                    objreq['obj_id'] = str(obj['_id'])
                    del objreq['iid']
                    del objreq['_id']
                    objreq['image_set_id'] = objreq['image_set_iid']
                    del objreq['image_set_iid']
                    objreq['requesting_organization_id'] = objreq['requesting_organization_iid']
                    del objreq['requesting_organization_iid']
                    self.response(200, 'CV Request found.',  objreq)
                else:
                    self.response(404, 'CV Request object not found.')
        else:
            objs = yield self.CVRequests.find().skip(self.skip).limit(self.limit).to_list(None)
            output = list()
            for x in objs:
                obj = dict(x)
                obj['obj_id'] = str(x['_id'])
                del obj['_id']
                self.switch_iid(obj)
                obj['image_set_id'] = obj['image_set_iid']
                del obj['image_set_iid']
                obj['requesting_organization_id'] = obj['requesting_organization_iid']
                del obj['requesting_organization_iid']
                output.append(obj)
            self.response(200, 'CV Requests found.', output)

    @api_authenticated
    def post(self, *kwargs):
        self.response(400, 'To create a CV Request you must POST to /imagesets/:id/cvrequest.')

    @api_authenticated
    def put(self, req_id=None):
        self.response(400, 'CV Requests are created and updated automatically.')

    @asynchronous
    @coroutine
    @api_authenticated
    def delete(self, req_id=None):
        # delete a req
        if req_id:
            query = self.query_id(req_id)
            updobj = yield self.CVRequests.find_one(query)
            if updobj:
                # removing cvrequest and cvresult related and they will be added in
                # a history collection
                try:
                    # get cvresult if it exists
                    cvres = yield self.CVResults.find_one({'cvrequest_iid': req_id})
                    if cvres:
                        info(cvres)
                        idcvres = ObjId(cvres['_id'])
                        del cvres['_id']
                        info(cvres)
                        newhres = yield self.db.cvresults_history.insert(cvres)
                        info(newhres)
                        cvres = yield self.CVResults.remove({'_id': idcvres})
                    del updobj['_id']
                    newhreq = yield self.db.cvrequests_history.insert(updobj)
                    info(newhreq)
                    cvreq = yield self.CVRequests.remove(query)
                    info(cvreq)
                    self.response(200, 'CV Request successfully deleted.')
                except Exception as e:
                    self.response(500, 'Fail to delete cvrequest.')
            else:
                self.response(404, 'CV Request not found.')
        else:
            self.response(400, 'Remove requests (DELETE) must have a resource ID.')

    @asynchronous
    @engine
    def list(self, objs, callback=None):
        """ Implements the list output used for UI in the website
        """
        output = list()
        cvresl = yield self.CVResults.find().to_list(None)
        cvresd = dict()
        for cvres in cvresl:
            cvresd[cvres['cvrequest_iid']] = {'cvres_id': cvres['iid'],
                                              'cvres_obj_id': str(cvres['_id'])}
        for x in objs:
            obj = dict()
            obj['cvreq_id'] = x['iid']
            obj['cvreq_obj_id'] = x['_id']
            obj['status'] = x['status']
            obj['imageset_id'] = x['image_set_iid']
            obj['organization_id'] = x['requesting_organization_iid']
            if x['iid'] in cvresd.keys():
                obj['cvres_id'] = cvresd[x['iid']]['cvres_id']
                obj['cvres_obj_id'] = cvresd[x['iid']]['cvres_obj_id']
            else:
                obj['cvres_id'] = None
                obj['cvres_obj_id'] = None
            output.append(obj)
        callback(output)
