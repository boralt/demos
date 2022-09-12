#######################################################################
# FUNGIBLE, INC. CONFIDENTIAL AND PROPRIETARY
#
# Copyright (C) 2020 by Fungible, Inc.
# This work is the property of Fungible, Inc. (Company).
#
# It contains proprietary information and trade secrets of the Company.
# Disclosure, use, or reproduction without the prior written approval
# of the Company is prohibited. All rights reserved.
#######################################################################

import swagger_client as fungible_intent_api
import bmv.bmv_dao
import json
import dcc_logger
import uuid
import traceback
from bmv.bmv_model import MacEvent

log = dcc_logger.DccLogger(__name__)

class BmvException(Exception):
    pass


class BmvApiInterface:
    def __init__(self, name, dao, network_api ):
        self.name = name
        self.dao = dao
        self.network_api = network_api
        self.delete_list = []
        self.upsert_list = []
        self.dpus_unavailable = {}
        self.request_params = {"_request_timeout":5}

    def get_dpus_unavailable(self):
        return  self.dpus_unavailable

    def _is_dpu_failed(self, res):
        if not hasattr(res, "status"):
            return False
        if res.status == True or res.status == 200:
            return False
        if type(res) == fungible_intent_api.rest.ApiException:
            jsonData = json.loads(res.body)
            message = jsonData.get("message")
        else :
            jsonData = res.data
            message = jsonData.get("message")
        return message == "DPU context not found" or message == "Network element with given DPU id is inactive"

    def _is_not_found(self, res):
        if type(res) == fungible_intent_api.rest.ApiException:
            if  res.status != 404:
                return False
            jsonData = json.loads(res.body)
            message = jsonData.get("message")
            return message.find("Delete object not found")>=0
        return False

    def fetch_uuid(self, res):
        if type(res) == fungible_intent_api.models.response_data_with_create_uuid.ResponseDataWithCreateUuid:
            result=res.data.uuid
        else:
            jsonData = json.loads(res.data)
            result =  jsonData.get("data")
            if result:
                result = result.get("uuid")
        return result

    def delete_bmv_object(self, record, keepInDcc):
        fc_dpu_id = self._get_fc_dpu_id(record)
        log.info('BmvApiInterface.delete_bmv_object.' + self.name + '.1',
                 'deleting %s %s on dpu %s', self.name,
                 self._get_entity_name(record), fc_dpu_id)

        try:
            if self.is_static(record):
                return True
            if self.is_no_fun(record) and not keepInDcc:
                self._do_delete(record)
                return True

            do_delete = True
            if self._get_bmv_uuid(record):
               try:
                  self._send_delete(record)
                  log.info('BmvApiInterface.delete_bmv_object.' + self.name + '.2',
                         'Deleted %s %s on dpu %s',
                     self.name,
                     self._get_entity_name(record),
                     fc_dpu_id)
               except Exception as e:
                   log.info('BmvApiInterface.delete_bmv_object.' + self.name + '.3',
                            ''.join(traceback.format_exception(None, e, e.__traceback__)))
                   do_delete = False
                   if self._is_dpu_failed(e):
                       self.dpus_unavailable[fc_dpu_id]=True
                   elif self._is_not_found(e):
                       log.info('networking.run_bmv_sync.' + self.name + '.4', "Deleted as not found")
                       do_delete = True
            else:
               log.info('BmvApiInterface.delete_bmv_object.' + self.name + '.5',
                         'Deleting before created %s %s on dpu %s',
                     self.name,
                     self._get_entity_name(record),
                     fc_dpu_id)

            log.info('BmvApiInterface.delete_bmv_object.' + self.name + '.6', "Looking to delete %s", do_delete)
            if do_delete:
                if keepInDcc:
                    self._do_unlink(record)
                else:
                    self._do_delete(record)
            return do_delete
        except Exception as e:
            log.info('BmvApiInterface.delete_bmv_object.' + self.name + '.7',
                 ''.join(traceback.format_exception(None, e, e.__traceback__)))
        return False

    def insert_bmv_object(self, record):
        fc_dpu_id = self._get_fc_dpu_id(record)
        if fc_dpu_id in self.dpus_unavailable:
            return
        log.info('BmvApiInterface.insert_bmv_object.' + self.name + '.1',
                 'upserting dmac %s on dpu %s',
                 self._get_entity_name(record),
                 fc_dpu_id)
        try:
            if self.is_no_fun(record):
                # make it easily recognizable
                bmv_uuid = uuid.uuid4()
                bmv_uuid = uuid.UUID(fields=(0x0, bmv_uuid.fields[1], bmv_uuid.fields[2], bmv_uuid.fields[3],
                                             bmv_uuid.fields[4], bmv_uuid.fields[5]))
                self._do_place( record, fc_dpu_id, bmv_uuid)
                return
            res = self._send_upsert(record)
            bmv_uuid=self.fetch_uuid(res)
            if bmv_uuid:
                log.info('BmvApiInterface.insert_bmv_object.' + self.name + '.2',
                         'Placing %s %s on dpu %s with uuid %s',
                         self.name,
                         self._get_entity_name(record),
                         fc_dpu_id,
                         bmv_uuid)
                self._do_place( record, fc_dpu_id, bmv_uuid)
            elif self._is_dpu_failed(res):
                self.dpus_unavailable[fc_dpu_id]=True
                log.info('BmvApiInterface.insert_bmv_object.' + self.name + '.3',
                         'Failng dpu %s due to response', fc_dpu_id, str(res))
        except Exception as e:
            if type(e) == BmvException:
                log.info('BmvApiInterface.insert_bmv_object.' + self.name + '.4',
                         'Failing in dpu %s due to %s', fc_dpu_id, e.args[0])
            if self._is_dpu_failed(e):
                self.dpus_unavailable[fc_dpu_id]=True
            log.info('BmvApiInterface.insert_bmv_object.' + self.name + '.5',
                    ''.join(traceback.format_exception(None, e, e.__traceback__)))

    def is_no_fun(self, record):
        ''' This entry is not handled by intent api '''
        return False

    def is_static(self, record):
        ''' This entry is not handled by intent api and is not deleted '''
        return False

    def _do_sync(self):
        return False

    def run_bmv_sync(self):
        self.dpus_unavailable = {}
        res = self._do_sync()

        log.debug('BmvApiInterface.run_bmv_sync.' + self.name + '.0',
                     'sync result %s', res)

        # unlink rows that are not in intent API and need to be deleted
        self._remove_stale_records()
        self.update_list = [item for item in self._get_update_list()]
        self.delete_list = [item for item in self._get_delete_list()]
        self.upsert_list = [item for item in self._get_upsert_list()]

        for record in self.update_list:
            #delete from intent api but keep in dcc
            self.delete_bmv_object(record, True)
            self.insert_bmv_object(record)

        for record in self.delete_list:
            self.delete_bmv_object(record, False)

        for record in self.upsert_list:
            self.insert_bmv_object(record)

    # used with insert or update command
    def _get_upsert_list(self):
        return []

    # need to be deleted and then re-inserted (optional)
    def _get_update_list(self):
        return []

    def _remove_stale_records(self):
        pass

    def _get_delete_list(self):
        return []

    def _get_fc_dpu_id(self, record):
        return record["fc_dpu_id"]

    def _get_entity_name(self, record):
        return record["dcc_uuid"]

    def _get_bmv_uuid(self, record):
        pass

    def _send_delete(self, record):
        pass

    def _send_upsert(self, record):
        return {}

    def _do_delete(self, record):
        pass

    # remove FC intent api linkage.
    # only needed if _get_update_list is implemented (optional)
    def _do_unlink(self, record):
        pass

    def _do_place(self, record, fc_dpu_id, bmv_uuid):
        return

class BmvVpcInterface(BmvApiInterface):
    def __init__(self,  dao, network_api ):
        super().__init__("vpc", dao, network_api)

    def _send_upsert(self, record):
        return self.network_api.create_bmv_vpc(self._get_fc_dpu_id(record),
                             { "name":record["dcc_uuid"] ,
                               "admin_state": "UP",
                               "dhcp_relay_server": "1.1.1.1",
                               "l3_vnid": 0,
                               "tenant_name": ""}, **self.request_params)
    def _send_delete(self, record):
        return self.network_api.delete_bmv_vpc(self._get_fc_dpu_id(record),
                                               self._get_bmv_uuid(record), **self.request_params)

    def _get_bmv_uuid(self, record):
        return record["bmv_vpc_uuid"]

    def _get_upsert_list(self):
        return self.dao.get_pending_vpcs()

    def _get_delete_list(self):
        return self.dao.get_deleted_vpcs()

    def _do_place(self, record, fc_dpu_id, bmv_uuid):
        self.dao.place_vpc( record["dcc_uuid"], fc_dpu_id, bmv_uuid)
        return

    def _do_delete(self, record):
        self.dao.delete_vpc(self._get_bmv_uuid(record))
        pass

    def _do_sync(self):
        self.dao.sync_vpcs()

    def is_no_fun(self, record):
        return  record["model"]=="gw"

    def is_static(self, record):
        return False



class BmvSubnetInterface(BmvApiInterface):
    def __init__(self,  dao, network_api ):
        super().__init__("subnet", dao, network_api)

    def _send_upsert(self, record):
        return self.network_api.create_bmv_subnets(self._get_fc_dpu_id(record),
                              {
                                "name":record["dcc_uuid"],
                                "admin_state": "UP",
                                "cidr": "",
                                "dhcp_relay_enabled": True,
                                "dhcp_relay_server": "",
                                "gateway_ip": record["gateway"],
                                "gateway_mac": "00:00:00:00:00:00",
                                "ip_version": 4,
                                "l2_vnid": record["vxlan_id"],
                                "vlan_id": record["vlan_id"],
                                "tenant_name": "",
                                "vpc_name": record["dcc_vrf_uuid"]
                                  }, **self.request_params)
    def _send_delete(self, record):
        return self.network_api.delete_bmv_subnets(self._get_fc_dpu_id(record),
                                                   self._get_bmv_uuid(record), **self.request_params)
    def _get_bmv_uuid(self, record):
        return record["bmv_subnet_uuid"]

    def _get_upsert_list(self):
        return self.dao.get_pending_subnets()

    def _get_delete_list(self):
        return self.dao.get_deleted_subnets()

    def _do_place(self, record, fc_dpu_id, bmv_uuid):
        self.dao.place_subnet( record["dcc_uuid"], fc_dpu_id, bmv_uuid)
        return

    def _do_delete(self, record):
        self.dao.delete_subnet(self._get_bmv_uuid(record))
        pass

    def _do_sync(self):
        self.dao.sync_subnets()

    def is_no_fun(self, record):
        return  record["model"]=="gw"

    def is_static(self, record):
        return False


class BmvNicInterface(BmvApiInterface):
    def __init__(self,  dao, network_api ):
        super().__init__("nic", dao, network_api)
        self.last_vf = -1

    def _get_entity_name(self, record):
        return record["dcc_nic_uuid"]

    def _send_upsert(self, record):
        # Temporary hack here
        hu_id = record["hu"]
        if record["fc_model"] == "FS1600-0":
            hu_id = 2
        pf = record["pf"]
        # temporary hack fc_model is manually modified in database
        if record["fc_model"] == "FS1600-01" or record["fc_model"] == "FS1600-0" :
            pf = 0

        # vf resource is currenly managed by high level
        #free_vf_list = [item for item in self.dao.get_free_vf(record["dcc_dpu_uuid"])]
        #if len(free_vf_list)==0:
        #    raise BmvException("Out of VF resource")
        #record["vf"]=int(free_vf_list[0]["num"])

        record["vf"] = record["vf"]

        data={ "name":"nic:"+self._get_entity_name(record),
                                "admin_state": "UP",
                                "allowed_vlans": "",
                                "arp_suppression_on": True,
                                "bum_broadcast_on": True,
                                "dhcp_relay_enabled": True,
                                "dhcp_relay_server": "",
                                "dvr_enabled": True,
                                "mac_address": record["macaddress"],
                                "mac_filtering_on": True,
                                "overlay_type": "BMVCOMPOSER",
                                "promiscous_mode_on": True,
                                "subnet_name": record["dcc_network_uuid"],
                                "tenant_name": "",
                                "vpc_name": record["dcc_vrf_uuid"],
                                "hu_id": hu_id,
                                "controller_id": record["controller"],
                                "pf_number": pf,
                                "vf_number": record["vf"]}

        log.info('networking.BmvNic._send_upsert.1',
                 'sending to dpu=%s\ndata=%s\nvf',
                 self._get_fc_dpu_id(record), data)


        return self.network_api.create_bmv_nics(self._get_fc_dpu_id(record), data, **self.request_params)

    def _send_delete(self, record):
        return self.network_api.delete_bmv_nics(self._get_fc_dpu_id(record),
                                                self._get_bmv_uuid(record), **self.request_params)

    def _get_bmv_uuid(self, record):
        return record["bmv_nic_uuid"]

    def _get_upsert_list(self):
        return self.dao.get_pending_nics()

    def _get_delete_list(self):
        return self.dao.get_deleted_nics()

    def _do_place(self, record, fc_dpu_id, bmv_uuid):
        self.dao.place_nic( record["dcc_nic_uuid"], bmv_uuid, record["vf"])
        return

    def _do_delete(self, record):
        self.dao.delete_nic(self._get_bmv_uuid(record))
        pass

    def _do_sync(self):
        self.dao.sync_nics()

    def is_no_fun(self, record):
        return  record["vf"]==-1

    def is_static(self, record):
        return record["vf"]==-1


class BmvNextHopInterface(BmvApiInterface):
    def __init__(self,  dao, network_api ):
        super().__init__("nexthop", dao, network_api)

    def _get_entity_name(self, record):
        return record["dcc_network_uuid"]+ "/" + record["remote_ip"]

    def _get_fc_dpu_id(self, record):
        return record["fc_dpu_id_local"]

    def _send_upsert(self, record):
        return self.network_api.create_bmv_nexthops(self._get_fc_dpu_id(record),
                              {
                                "name":self._get_entity_name(record),
                                "admin_state": "UP",
                                "composed_nic": "",
                                "ip_version": 4,
                                "state": 0,
                                "subnet_name": record["dcc_network_uuid"],
                                "tenant_name":"",
                                "vpc_name": record["dcc_vrf_uuid"],
                                "local_vxlan_gw_ip": record["local_ip"],
                                  "remote_vxlan_gw_ip": record["remote_ip"]}, **self.request_params)

    def _send_delete(self, record):
        return self.network_api.delete_bmv_nexthops(self._get_fc_dpu_id(record),
                                                    self._get_bmv_uuid(record), **self.request_params)

    def _get_bmv_uuid(self, record):
        return record["bmv_next_hop_uuid"]

    def _get_upsert_list(self):
        return self.dao.get_pending_nexthops()

    def _get_delete_list(self):
        return self.dao.get_deleted_nexthops()

    def _do_place(self, record, fc_dpu_id, bmv_uuid):
        self.dao.place_nexthops( record["dcc_network_uuid"], fc_dpu_id, record["remote_ip"],  bmv_uuid)
        return

    def _do_delete(self, record):
        self.dao.delete_nexthop(record["dcc_network_uuid"], record["fc_dpu_id_local"], record["fc_dpu_id_remote"])
        pass

    def _do_sync(self):
        self.dao.sync_nexthops()


class BmvDmacInterface(BmvApiInterface):
    def __init__(self,  dao, network_api ):
        super().__init__("dmac", dao, network_api)

    def _get_entity_name(self, record):
        return record["mac"]
        #return record["dcc_network_uuid"]+ "/" + record["mac"]


    def _get_fc_dpu_id(self, record):
        return record["fc_dpu_id_local"]

    def _send_upsert(self, record):
        return self.network_api.create_bmv_dmac(self._get_fc_dpu_id(record),
                               {
                                "admin_state": "UP",
                                "mac_address":record["mac"],
                                "nexthop_name": record["dcc_network_uuid"]+ "/" + record["remote_ip"],
                                "bum_broadcast_on":"true",
                                "tenant_name": "",
                                "subnet_name": record["dcc_network_uuid"],
                                   "vlan_id": record["vlan_id"]}, **self.request_params)

    def _send_delete(self, record):
        return self.network_api.delete_bmv_dmac(self._get_fc_dpu_id(record),
                                                self._get_bmv_uuid(record), **self.request_params)

    def _get_bmv_uuid(self, record):
        return record["bmv_dmac_uuid"]

    def _get_update_list(self):
        return self.dao.get_updating_dmac()

    def _remove_stale_records(self):
        self.dao._remove_dmac_stale_records()

    def _get_unlink_list(self):
        return self.dao.get_unlink_dmac()

    def _get_upsert_list(self):
        return self.dao.get_pending_dmac()

    def _get_delete_list(self):
        return self.dao.get_deleted_dmac()

    def _do_place(self, record, fc_dpu_id, bmv_uuid):
        self.dao.place_dmac( record["dcc_network_uuid"], fc_dpu_id, record["mac"],  bmv_uuid)
        return

    def _do_delete(self, record):
        self.dao.delete_dmac(record["dcc_network_uuid"], record["fc_dpu_id_local"], record["fc_dpu_id_remote"], record["mac"])
        pass

    def _do_unlink(self, record):
        self.dao.unlink_dmac(self._get_bmv_uuid(record))
        pass

    def _do_sync(self):
        self.dao.sync_dmac()


class BmvMacTblInterface:
    def __init__(self,  dao, network_api ):
        self.dao = dao
        self.network_api = network_api
        self.request_params = {"_request_timeout":5}
    def poll_dpu(self, fc_dpu_id=None):
        if not fc_dpu_id:
            raise BmvException("BmvMacTblInterface polling invalid endpoint")
        try:
            res = self.network_api.get_bmv_mactbl_all(fc_dpu_id, **self.request_params)
            #import pdb; pdb.set_trace()
            ar_entries = []
            if res.status and res.data:
                if type(res) == fungible_intent_api.models.response_data_with_bmv_mactbl.ResponseDataWithBmvMactbl:
                    for data_entry in res.data:
                        nic_name = data_entry.associated_nic
                        sequence_number = data_entry.sequence_number
                        log.debug('networking.BmvMacTblInterface.poll_dpu.1', "Got %s %s", nic_name, data_entry.mac_address)
                        # dcc nic name format "nic:<dcc_nic_uuid>
                        nic_name_split = nic_name.split(":")
                        if len(nic_name_split)==2 and nic_name_split[0]=="nic":
                            uuid_obj = None
                            try:
                                uuid_obj = uuid.UUID(nic_name_split[1])
                            except ValueError:
                                pass
                            if uuid_obj:
                                ar_entries.append(MacEvent(dpu_id=fc_dpu_id,
                                                           nic_uuid=nic_name_split[1],
                                                           mac=data_entry.mac_address,
                                                           sequence_number=sequence_number))
                                #ar_entries.append((nic_name_split[1],
                                #                   data_entry.mac_address,
                                #                   fc_dpu_id,
                                #                   False,
                                #                   False,
                                #                   sequence_number))
            #generate update

            self.dao.mac_table_update(fc_dpu_id, ar_entries)


        except Exception as e:
            log.info('networking.BmvMacTblInterface.poll_dpu'  + '.1',
                 ''.join(traceback.format_exception(None, e, e.__traceback__)))


    def erase_stale_macs(self):
        self.dao.mac_table_update_migration()
        expire_list = [item  for item in self.dao.get_macs_forced_expiring()]
        # send expire to all active dpus
        for expire_item in expire_list:
            try:
                self.network_api.delete_bmv_mactbl_entry(dpu_id=expire_item["fc_dpu_id"],
                                                         bmv_mac_seq_num=expire_item["sequence_number"], **self.request_params)
            except Exception as e:
                log.info('networking.BmvMacTblInterface.erase_stale_macs'  + '.1',
                 ''.join(traceback.format_exception(None, e, e.__traceback__)))

        self.dao.erase_stale_macs()

    def process_event(self, mac_event):
        if not mac_event.is_delete:
            #discovered mac
            self.dao.mac_entry_update(mac_event)
        else:
            #delete mac
            self.dao.mac_table_pend_entry(dpu_id=mac_event.dpu_id, nic_uuid=mac_event.nic_uuid, mac=mac_event.mac)

class BgpInterface:
    def __init__(self,  dao, network_api ):
        self.dao = dao
        self.network_api = network_api

    def sync_to_dpus(self):
        return self.dao.sync_bgp_to_dpu()

    def sync_to_dmac(self):
        return self.dao.sync_bgp_to_bmv_dmac()

    def sync_to_bgp(self):
        return self.dao.sync_bmv_bgp_routes()




class BmvSynchronizer:
    def __init__(self, dao=None, api_client=None):
        self.dao = dao
        self.network_api=fungible_intent_api.NetworkApi(api_client)
        # synchronizers
        self.vpc = BmvVpcInterface(self.dao, self.network_api)
        self.subnet = BmvSubnetInterface(self.dao, self.network_api)
        self.nic = BmvNicInterface(self.dao, self.network_api)
        self.nexthop = BmvNextHopInterface(self.dao, self.network_api)
        self.dmac = BmvDmacInterface(self.dao, self.network_api)
        self.mactbl = BmvMacTblInterface(self.dao, self.network_api)
        self.bgp = BgpInterface(self.dao, self.network_api)

    def fetch_uuid(self, res):
        jsonData = json.loads(res.data)
        result =  jsonData.get("data")
        if result:
            result = result.get("uuid")
        return result

    def is_dpu_failed(self, res):
        jsonData = json.loads(res.data)
        status =  jsonData.get("status")
        return status == 503 or status == 403

    def process_vpc_sync(self):
        self.vpc.run_bmv_sync()
        return self.vpc.get_dpus_unavailable()

    def process_subnet_sync(self):
        self.subnet.run_bmv_sync()
        return self.subnet.get_dpus_unavailable()

    def process_nic_sync(self):
        self.nic.run_bmv_sync()
        return self.nic.get_dpus_unavailable()

    def process_nexthop_sync(self):
        self.nexthop.run_bmv_sync()
        return self.nexthop.get_dpus_unavailable()

    def process_dmac_sync(self):
        self.dmac.run_bmv_sync()
        return self.dmac.get_dpus_unavailable()

    def process_mactbl_sync(self, fc_dpu_id):
        self.mactbl.poll_dpu(fc_dpu_id)

    def process_event(self, mac_event):
        self.mactbl.process_event(mac_event)

    def erase_stale_macs(self):
        self.mactbl.erase_stale_macs()

    # overall sync steps used for testing
    def process_bgp_sync(self):
        self.bgp.sync_to_dpus()
        self.process_nexthop_sync()
        self.bgp.sync_to_dmac()
        self.bgp.sync_to_bgp()

    def process_bgp_to_dpu_sync(self):
        self.bgp.sync_to_dpus()

    def process_bgp_to_dmac_sync(self):
        self.bgp.sync_to_dmac()

    def process_bmv_macs_to_bgp_sync(self):
        return self.bgp.sync_to_bgp()
