# Copyright 2015 - Alcatel-Lucent
#
# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""
https://docs.openstack.org/horizon/latest/contributor/tutorials/plugin.html
"""

""" This file will likely be necessary if creating a Django or Angular driven
    plugin. This file is intended to act as a convenient location for
    interacting with the new service this plugin is supporting.
    While interactions with the service can be handled in the views.py,
    isolating the logic is an established pattern in Horizon.
"""

from horizon.utils.memoized import memoized  # noqa
from keystoneauth1.identity.generic.token import Token
from keystoneauth1.session import Session
from keystoneauth1.identity import v3
from openstack_dashboard.api import base
from vitrageclient import client as vitrage_client
from contrib import action_manager

import ConfigParser
import logging
LOG = logging.getLogger(__name__)


@memoized
def vitrageclient(request, password=None):
    endpoint = base.url_for(request, 'identity')
    token_id = request.user.token.id
    tenant_name = request.user.tenant_name
    project_domain_id = request.user.token.project.get('domain_id', 'Default')
    auth = Token(auth_url=endpoint, token=token_id,
                 project_name=tenant_name,
                 project_domain_id=project_domain_id)
    session = Session(auth=auth, timeout=600)
    return vitrage_client.Client('1', session)

def mec_client(request):
    clientlist = []
    meclist = []

    setting = ConfigParser.ConfigParser()
    setting.read('/opt/stack/mecsetting/setting.conf')
    if setting.has_section('Default'):
        if setting.has_option('Default', 'meclist'):
            conf_actions = setting.get('Default', 'meclist').split(',')
            meclist = conf_actions
            for section in conf_actions:
                if setting.has_section(section):
                    option_list = setting.options(section)
                    print(option_list)
                    auth_url = ""
                    user_name = ""
                    password = ""
                    project_name = ""
                    project_domain = ""
                    user_domain = ""

                    for pro in option_list :
                        if 'auth_url' == pro :
                            auth_url = setting.get(section,pro)
                        elif 'user_name' == pro :
                            user_name = setting.get(section,pro)
                        elif 'password' == pro :
                            password = setting.get(section,pro)
                        elif 'project_name' == pro :
                            project_name = setting.get(section,pro)
                        elif 'project_domain_name' == pro :
                            project_domain = setting.get(section,pro)
                        elif 'user_domain_name' == pro :
                            user_domain = setting.get(section,pro)

                    v3_auth = v3.Password(auth_url=auth_url + "/v3",
                                          username=user_name,
                                          password=password,
                                          project_name=project_name,
                                          project_domain_name=project_domain,
                                          user_domain_name=user_domain)

                    v3_ses = Session(auth=v3_auth)
                    auth_token = v3_ses.get_token()

                    auth = Token(auth_url=auth_url,
                                  token=auth_token,
                                  project_name=project_name,
                                  project_domain_id=project_domain)
                    session = Session(auth=auth, timeout=600)
                    clientlist.append(vitrage_client.Client('1', session))


    return clientlist,meclist

def getMECRca(request):
    pass

def topology(request, query=None, graph_type='tree', all_tenants='false',
             root=None, limit=None):
    LOG.info("--------- CALLING VITRAGE_CLIENT ---request %s", str(request))
    LOG.info("--------- CALLING VITRAGE_CLIENT ---query %s", str(query))
    LOG.info("------ CALLING VITRAGE_CLIENT --graph_type %s", str(graph_type))
    LOG.info("---- CALLING VITRAGE_CLIENT --all_tenants %s", str(all_tenants))
    LOG.info("--------- CALLING VITRAGE_CLIENT --------root %s", str(root))
    LOG.info("--------- CALLING VITRAGE_CLIENT --------limit %s", str(limit))

    mecclient,meclist = mec_client(request)
    print("####################### MEC LIST ", meclist)

    cluster_index = 0
    now_cluster = 0

    entity_num = 0
    link_num = 0
    first = True
    second = False
    first_client = None
    rca_cnt = -1
    client_cnt = -1

    for client in mecclient :
        global first,first_client,rca_cnt,now_cluster,client_cnt,cluster_index, entity_num,second,link_num
        rca_cnt += 1
        client_cnt += 2
        rcaclient = client.topology.get(query=query,
                               graph_type=graph_type,
                               all_tenants=all_tenants,
                               root=root,
                               limit=limit)

        if first == True:
            first_client = rcaclient
            ### GET Cluster Index
            for entity in rcaclient['nodes']:
                if entity['vitrage_category'] != 'ALARM' :
                    if entity['id'] == 'OpenStack Cluster':
                        cluster_index = entity['graph_index']
                if entity['id'] == 'nova':
                    entity['name'] = meclist[rca_cnt] + '_nova'
                    entity['id'] = meclist[rca_cnt] + '_nova'
            first = False
            second = True
            entity_num += (len(rcaclient['nodes']))
            link_num += (len(rcaclient['nodes']))
        else :
            ####### SET Other RCA ENTITY
            now_cluster = 0
            t_now_entitylist = []
            s_now_entitylist = []
            now_entitylist = []
            clu = False

            ####### SET now RCA entity list
            for entity in rcaclient['nodes']:
                global clu,cluster_index
                if entity['id'] == 'OpenStack Cluster':
                    now_cluster = entity['graph_index']
                    clu = True
                if clu == True and entity['id'] != 'OpenStack Cluster':
                    s_now_entitylist.append(entity['id'])
                    t_now_entitylist.append(entity['id'])
                    now_entitylist.append(entity['id'])
            for j in range(len(rcaclient['links'])):
                rcaclient['links'][j]['s_cha'] = True
                rcaclient['links'][j]['t_cha'] = True

            for j in range(len(rcaclient['links'])):
                if rcaclient['links'][j]['source'] == now_cluster and \
                                rcaclient['links'][j]['s_cha'] == True:
                    rcaclient['links'][j]['source'] = cluster_index
                    rcaclient['links'][j]['s_cha'] = False

                if rcaclient['links'][j]['target'] == now_cluster \
                        and rcaclient['links'][j]['t_cha'] == True:
                    rcaclient['links'][j]['target'] = cluster_index
                    rcaclient['links'][j]['t_cha'] = False
                if rcaclient['links'][j]['source'] != now_cluster and \
                                rcaclient['links'][j]['s_cha'] == True:
                    if rcaclient['links'][j]['source'] < now_cluster:
                        rcaclient['links'][j]['source'] += link_num
                        rcaclient['links'][j]['s_cha'] = False
                    else:
                        rcaclient['links'][j]['source'] += (link_num-1)
                        rcaclient['links'][j]['s_cha'] = False

                if rcaclient['links'][j]['target'] != now_cluster and \
                            rcaclient['links'][j]['t_cha'] == True:
                    if rcaclient['links'][j]['target'] < now_cluster:
                        rcaclient['links'][j]['target'] += link_num
                        rcaclient['links'][j]['t_cha'] = False
                    else :
                        rcaclient['links'][j]['target'] += (link_num-1)
                        rcaclient['links'][j]['t_cha'] = False

            ####### ADD RCA tree at First Tree
            for entity in rcaclient['nodes']:
                if entity['vitrage_category'] == 'ALARM':
                    pass
                elif entity['vitrage_category'] != 'ALARM':
                    if entity['id'] not in now_entitylist:
                        entity['graph_index'] += entity_num
                    else:
                        entity['graph_index'] += entity_num -1

                if entity['id'] == 'nova':
                    entity['name'] = meclist[rca_cnt] + '_nova'
                    entity['id'] = meclist[rca_cnt] + '_nova'

                if entity['id'] != 'OpenStack Cluster':
                    first_client['nodes'].append(entity)

            for j in range(len(rcaclient['links'])):
                del rcaclient['links'][j]['s_cha']
                del rcaclient['links'][j]['t_cha']

            for j in range(len(rcaclient['links'])):
                first_client['links'].append(rcaclient['links'][j])

            entity_num += (len(rcaclient['nodes'])-1)
            if second == True:
                link_num += (len(rcaclient['nodes'])-1)
                print("&+******************* link_num",link_num)
                second = False
    rca_cnt = -1
    return first_client

def alarms(request, vitrage_id='all', all_tenants='false'):
    return vitrageclient(request).alarm.list(vitrage_id=vitrage_id,
                                             all_tenants=all_tenants)


def alarm_counts(request, all_tenants='false'):
    counts = vitrageclient(request).alarm.count(all_tenants=all_tenants)
    counts['NA'] = counts.get("N/A")
    return counts


def rca(request, alarm_id, all_tenants='false'):
    return vitrageclient(request).rca.get(alarm_id=alarm_id,
                                          all_tenants=all_tenants)


def templates(request, template_id='all'):
    if template_id == 'all':
        return vitrageclient(request).template.list()
    return vitrageclient(request).template.show(template_id)



def actions(request, action, nodetype):
    endpoint = base.url_for(request, 'identity')
    token_id = request.user.token.id
    tenant_name = request.user.tenant_name
    project_domain_id = request.user.token.project.get('domain_id', 'Default')
    auth = Token(auth_url=endpoint, token=token_id,
                 project_name=tenant_name,
                 project_domain_id=project_domain_id)
    session = Session(auth=auth, timeout=600)
    result = action_manager.ActionManager.getinfo(session, str(action),request)
    return result

def action_request(request, action, requestdict):
    endpoint = base.url_for(request, 'identity')
    token_id = request.user.token.id
    tenant_name = request.user.tenant_name
    project_domain_id = request.user.token.project.get('domain_id', 'Default')
    auth = Token(auth_url=endpoint, token=token_id,
                 project_name=tenant_name,
                 project_domain_id=project_domain_id)

    session = Session(auth=auth, timeout=600)
    result = action_manager.ActionManager.execute(session, str(action),requestdict)
    return result

def action_setting(request):
    setting = ConfigParser.ConfigParser()
    setting.read('/etc/vitrage-dashboard/setting.conf')
    actionlist = []
    urllist = {}
    if setting.has_section('Default'):
        if setting.has_option('Default', 'actions'):
            conf_actions = setting.get('Default', 'actions').split(',')

            for section in conf_actions:
                result = None
                if setting.has_section(section):
                    option_list = setting.options(section)
                    matching = [pro for pro in option_list
                                if ('url' in pro)]
                    if matching:
                        urllist[section] = setting.get(section,
                                                           matching[0])
                else:
                    result = action_manager.ActionManager.importcheck(section,request)

                if result:
                    actionlist.append(section.capitalize())
        return [actionlist, urllist]



