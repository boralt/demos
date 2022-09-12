import pytest
#from tests.controllers.mocks import *
from dcc_pytest_testrail.plugin import pytestrail
import uuid
import swagger_client as fungible_intent_api

import urllib3
import time

import xml.etree.ElementTree as ET

from bmv.bmv_sync_generators import BmvSynchronizer
from bmv.xmpp_client import XmppClient
from bmv.postgres_queries import GET_BGP_ROUTE_PENDING
from bmv.bmv_model import MacEvent
from service.config import Config
from service.logging import Logging

# to enable full logging in test output do "Logging.setup(_FULL_LOGGING);" in test case
_FULL_LOGGING= {
  "clients.ipam_client": {
    "level": "DEBUG",
      "handlers": ["syslog", "console"]
  },
  "clients.k8s_client": {
      "level": "DEBUG",
      "handlers": ["syslog", "console"]
  },
  "service.dao": {
    "level": "DEBUG",
    "handlers": ["syslog", "console"]
  },
  "service.controllers": {
    "level": "DEBUG",
    "handlers": ["syslog", "console"]
  },
  "bmv.bmv_loop": {
    "level": "DEBUG",
    "handlers": ["syslog", "console"]
  },
  "bmv.bmv_sync_generators": {
    "level": "DEBUG",
    "handlers": ["syslog", "console"]
  },
  "bmv.gateway_client": {
    "level": "DEBUG",
    "handlers": ["syslog", "console"]
  },
  "bmv.xmpp_client": {
    "level": "DEBUG",
    "handlers": ["syslog", "console"]
  }
}


def is_valid_uuid(uuid_to_test, version=1):
    try:
        uuid_obj = uuid.UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    except TypeError:
        return False
    return str(uuid_obj) == uuid_to_test


class MockApiClient:
    def __init__(self, mocker):
        #self.client_side_validation=True
        mocker.patch.object(fungible_intent_api.ApiClient, 'call_api')
        fungible_intent_api.ApiClient.call_api.side_effect=self.call_api
        self.counter_methods={}
        self.learned_mac_entries=[]
        self.call_record = []

    def call_api(self, resource_path, method,
                 path_params=None, query_params=None, header_params=None,
                 body=None, post_params=None, files=None,
                 response_type=None, auth_settings=None, async_req=None,
                 _return_http_data_only=None, collection_formats=None,
                 _preload_content=True, _request_timeout=None, _host=None,
                 _check_type=None):
        #import pdb; pdb.set_trace()
        if self.counter_methods.get(method):
            self.counter_methods[method] += 1
        else:
            self.counter_methods[method] = 1

        self.call_record.append({"resource_path":resource_path,
                                 "method":method,
                                 "path_params":path_params,
                                 "query_params":query_params,
                                 "header_params":header_params,
                                 "post_params":post_params})

        uuid_str = str(uuid.uuid1())

        if (resource_path=="/network/dpus/{dpu_id}/bmv_mactbl"):
            mac_table=[]
            index = 1
            for mac_entry in self.learned_mac_entries:
                index += 1
                mac_table.append(fungible_intent_api.models.bmv_mactbl.BmvMactbl(associated_nic="nic:"+mac_entry[1] , mac_address=mac_entry[0], tenant_name="", vlan_id=0, sequence_number=mac_entry[2]))
            return fungible_intent_api.models.response_data_with_bmv_mactbl.ResponseDataWithBmvMactbl(status=True, message="Ok", data=mac_table)
        else:
            return urllib3.response.HTTPResponse(body=b"{\"status\": true,\"message\": \"Ok\",\"data\": {\"uuid\":\""+ bytes(uuid_str, 'ascii') +b"\"}}", status=200)

    def find_api_calls(self, method=None, path=None):
        res = []
        for record in self.call_record:
            if record["method"] == method or method == None:
                if record["resource_path"] == path or path ==None:
                    res.append(record)
        return res

    def select_header_accept(self, accepts):
        """Returns `Accept` based on an array of accepts provided.

        :param accepts: List of headers.
        :return: Accept (e.g. application/json).
        """
        if not accepts:
            return

        accepts = [x.lower() for x in accepts]

        if 'application/json' in accepts:
            return 'application/json'
        else:
            return ', '.join(accepts)
    def select_header_content_type(self, content_types):
        """Returns `Content-Type` based on an array of content_types provided.

        :param content_types: List of content-types.
        :return: Content-Type (e.g. application/json).
        """
        if not content_types:
            return 'application/json'

        content_types = [x.lower() for x in content_types]

        if 'application/json' in content_types or '*/*' in content_types:
            return 'application/json'
        else:
            return content_types[0]

@pytest.fixture()
def mock_api_client(mocker):
    mock = MockApiClient(mocker)
    return mock

@pytest.mark.usefixtures('populate_database')
def test_create_vpc(mock_api_client):
    network_api=fungible_intent_api.NetworkApi()
    res = network_api.create_bmv_vpc("11:22:33:44:55:66", {"name":"aaa", "admin_state":"UP", "dhcp_relay_server":"", "l3_vnid":0, "tenant_id":"1"})
    print("Got={}".format(res.data))


@pytest.mark.usefixtures('populate_database')
def test_sync_vpc(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    res_list= test_dao.get_table("bmv_vpc_fanout")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_vpc_uuid")), "vpc {} uuid is invalid {}".format(row.get("dcc_uuid"), row.get("bmv_vpc_uuid"))
        assert row.get("update_pending")==False, "vpc {} still pending".format(row.get("dcc_uuid"))
    assert count==11
    assert mock_api_client.counter_methods=={"POST":11}


def delete_network_slice(dao):
    dao.exec_query_noreturn("DELETE FROM networking.network_nic WHERE network_uuid='34ede011-1d4b-11eb-adc1-0242ac120002' RETURNING *;")
    dao.exec_query_noreturn("DELETE FROM networking.network WHERE uuid='34ede011-1d4b-11eb-adc1-0242ac120002' RETURNING *;")
    dao.exec_query_noreturn("DELETE FROM networking.cidr_block WHERE uuid='34ede011-1d4b-11eb-adc1-0242ac120002' RETURNING *;")
    dao.exec_query_noreturn("DELETE FROM networking.vrf WHERE uuid='34ede011-1d4b-11eb-adc1-0242ac120002' RETURNING *;")

@pytest.mark.usefixtures('populate_database')
def test_delete_vpc(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()

    test_dao.dump_query("select * from networking.vrf")
    delete_network_slice(test_dao)
    test_dao.dump_query("select * from networking.vrf")
    mock_api_client.counter_methods={}
    sync.process_vpc_sync()
    res_list= test_dao.get_table("bmv_vpc_fanout")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_vpc_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "vpc {} still pending".format(row.get("dcc_uuid"))
        assert row.get("delete_pending")==False, "vpc {} still pending".format(row.get("dcc_uuid"))
    assert count==9
    assert mock_api_client.counter_methods=={"DELETE":2}

@pytest.mark.usefixtures('populate_database')
def test_sync_subnet(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    res_list= test_dao.get_table("bmv_subnet_fanout")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "subnet {} still pending".format(row.get("dcc_uuid"))
    assert count==11

@pytest.mark.usefixtures('populate_database')
def test_delete_subnet(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    delete_network_slice(test_dao)
    mock_api_client.counter_methods={}
    sync.process_subnet_sync()
    res_list= test_dao.get_table("bmv_subnet_fanout")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "subnet {} still pending".format(row.get("dcc_uuid"))
        assert row.get("delete_pending")==False, "subnet {} still pending".format(row.get("dcc_uuid"))
    assert count==9
    assert mock_api_client.counter_methods=={"DELETE":2}

@pytest.mark.usefixtures('populate_database')
def test_sync_nic(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    res_list= test_dao.get_table("bmv_nic")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_nic_uuid")), "nic {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_vpc_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "nic {} still pending".format(row.get("dcc_uuid"))
    assert count==11


@pytest.mark.usefixtures('populate_database')
def test_delete_nic(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    delete_network_slice(test_dao)
    mock_api_client.counter_methods={}
    sync.process_nic_sync()
    res_list= test_dao.get_table("bmv_nic")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_nic_uuid")), "nic {} uuid is invalid".format(row.get("dcc_nic_uuid"))
        assert row.get("update_pending")==False, "nic update {} still pending".format(row.get("dcc_uuid"))
        assert row.get("delete_pending")==False, "nic delete {} still pending".format(row.get("dcc_uuid"))
    assert count==9
    assert mock_api_client.counter_methods=={"DELETE":2}

@pytest.mark.usefixtures('populate_database')
def test_detach_nic(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()

    test_dao.exec_query_noreturn("UPDATE networking.network_nic set server_uuid=NULL  WHERE mac_addr='11:11:11:11:11:01' RETURNING *;")
    mock_api_client.counter_methods={}
    sync.process_nic_sync()
    res_list= test_dao.get_table("bmv_nic")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_nic_uuid")), "nic {} uuid is invalid".format(row.get("dcc_nic_uuid"))
        assert row.get("update_pending")==False, "nic update {} still pending".format(row.get("dcc_uuid"))
        assert row.get("delete_pending")==False, "nic delete {} still pending".format(row.get("dcc_uuid"))
    assert count==10
    assert mock_api_client.counter_methods=={"DELETE":1}
    #re-attach
    mock_api_client.counter_methods={}
    test_dao.exec_query_noreturn("UPDATE networking.network_nic set server_uuid='20e398fc-1d52-11eb-adc1-0242ac120002'  WHERE mac_addr='11:11:11:11:11:01' RETURNING *;")
    sync.process_nic_sync()
    res_list= test_dao.get_table("bmv_nic")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_nic_uuid")), "nic {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_vpc_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "nic {} still pending".format(row.get("dcc_uuid"))
    assert count==11
    assert mock_api_client.counter_methods=={"POST":1}


@pytest.mark.usefixtures('populate_database')
def test_sync_next_hop(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    res_list= test_dao.get_table("bmv_next_hop_fanout")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_next_hop_uuid")), "nic {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_subnet_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_vpc_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "nexthop {} still pending".format(row.get("dcc_uuid"))
    assert count==20

@pytest.mark.usefixtures('populate_database')
def test_delete_nexthop(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    delete_network_slice(test_dao)
    mock_api_client.counter_methods={}
    sync.process_nexthop_sync()
    res_list= test_dao.get_table("bmv_next_hop_fanout")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_next_hop_uuid")), "nexthop {} uuid is invalid".format(row.get("dcc_nic_uuid"))
        assert row.get("update_pending")==False, "nexthop update {} still pending".format(row.get("dcc_uuid"))
        assert row.get("delete_pending")==False, "nexthop delete {} still pending".format(row.get("dcc_uuid"))
    assert count==18
    assert mock_api_client.counter_methods=={"DELETE":2}

@pytest.mark.usefixtures('populate_database')
def test_sync_dmac(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()

    sync.process_dmac_sync()
    res_list= test_dao.get_table("bmv_dmac_fanout")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_dmac_uuid")), "nic {} uuid is {} invalid".format(row.get("dcc_uuid"), row.get("bmv_dmac_uuid"))
        assert is_valid_uuid(row.get("bmv_next_hop_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "dmac {}/{} still pending".format(row.get("dcc_network_uuid"), row.get("mac"))
    assert count==20


TEST_Q = ("SELECT network_nic.uuid, dpu_cache.dcc_uuid, network_nic.network_uuid,  bmv_subnet_fanout.bmv_vpc_uuid, bmv_subnet_fanout.bmv_subnet_uuid, network_nic.mac_addr, 0, 0, 0, 0, False, True "
    "FROM networking.network_nic network_nic, networking.network network, networking.dpu_cache dpu_cache, networking.bmv_vpc_fanout bmv_vpc_fanout, networking.cidr_block cidr_block, networking.bmv_subnet_fanout bmv_subnet_fanout "
    "WHERE network_nic.server_uuid=dpu_cache.server_uuid and network_nic.network_uuid=network.uuid and network.cidr_block_uuid=cidr_block.uuid and cidr_block.vrf_uuid=bmv_vpc_fanout.dcc_uuid and bmv_vpc_fanout.bmv_vpc_uuid=bmv_subnet_fanout.bmv_vpc_uuid and bmv_subnet_fanout.dcc_uuid=network_nic.network_uuid and bmv_subnet_fanout.fc_dpu_id=dpu_cache.fc_dpu_id")


@pytest.mark.usefixtures('populate_database')
def test_delete_dmac(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()
    delete_network_slice(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    mock_api_client.counter_methods={}
    sync.process_dmac_sync()
    res_list= test_dao.get_table("bmv_dmac_fanout")
    count = 0
    for row in res_list:
        count = count+1
        assert is_valid_uuid(row.get("bmv_dmac_uuid")), "dmac {} uuid is invalid".format(row.get("dcc_nic_uuid"))
        assert row.get("update_pending")==False, "dmac update {} still pending".format(row.get("dcc_uuid"))
        assert row.get("delete_pending")==False, "dmac delete {} still pending".format(row.get("dcc_uuid"))
    assert count==18
    assert mock_api_client.counter_methods=={"DELETE":2}


@pytest.mark.usefixtures('populate_database')
def test_dpu_offline(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    dpu_id_offline = "99:99:99:99:99:02"
    dpu_uuid_offline = 'ac1e9c92-1d60-11eb-adc1-0242ac120002'
    test_dao.set_dpu_unavailable(dpu_id_offline)
    sync.process_vpc_sync()
    sync.process_subnet_sync()

    #test_dao.dump_query(TEST_Q)
    #test_dao.dump_query("select * from networking.bmv_subnet_fanout")

    sync.process_nic_sync()

    sync.process_nexthop_sync()
    sync.process_dmac_sync()

    res_list= test_dao.get_table("bmv_vpc_fanout")
    count1 = 0
    count2 = 0
    for row in res_list:
        if row.get("fc_dpu_id") != dpu_id_offline:
            count1 = count1+1
            assert is_valid_uuid(row.get("bmv_vpc_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
            assert row.get("update_pending")==False, "vpc {} still pending".format(row.get("dcc_uuid"))
        else:
            count2 = count2 + 1
            assert not is_valid_uuid(row.get("bmv_vpc_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
            assert row.get("update_pending")==True, "vpc {} still pending".format(row.get("dcc_uuid"))
    assert count1==10
    assert count2==1


    res_list= test_dao.get_table("bmv_subnet_fanout")
    count1 = 0
    count2 = 0

    for row in res_list:
        if row.get("fc_dpu_id") != dpu_id_offline:
            count1 = count1+1
            assert is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
            assert row.get("update_pending")==False, "subnet {} still pending".format(row.get("dcc_uuid"))
        else:
            count2 = count2+1
            assert not is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
            assert not is_valid_uuid(row.get("bmv_vpc_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
            assert row.get("update_pending")==True, "subnet {} still pending".format(row.get("dcc_uuid"))

    assert count1==10
    assert count2==1

    res_list= test_dao.get_table("bmv_nic")
    count1 = 0
    count2 = 0
    for row in res_list:
        if row.get("dcc_dpu_uuid") != dpu_uuid_offline:
            count1 = count1+1
            assert is_valid_uuid(row.get("bmv_nic_uuid")), "nic {} uuid is invalid".format(row.get("dcc_nic_uuid"))
            assert is_valid_uuid(row.get("bmv_vpc_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_nic_uuid"))
            assert is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_nic_uuid"))
            assert row.get("update_pending")==False, "nic {} still pending".format(row.get("dcc_uuid"))
        else:
            count2 = count2+1
            assert not is_valid_uuid(row.get("bmv_nic_uuid")), "nic {} uuid is invalid".format(row.get("dcc_nic_uuid"))
            assert not is_valid_uuid(row.get("bmv_vpc_uuid")), "vpc uuid is valid for nic {} ".format(row.get("dcc_nic_uuid"))
            assert not is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_nic_uuid"))
            assert row.get("update_pending")==False, "nic {} still pending".format(row.get("dcc_uuid"))
    assert count1==10
    assert count2==0

    res_list= test_dao.get_table("bmv_next_hop_fanout")
    count1 = 0
    count2 = 0
    for row in res_list:
        if row.get("fc_dpu_id_local") != dpu_id_offline:
            count1 = count1+1
            assert is_valid_uuid(row.get("bmv_next_hop_uuid")), "nic {} uuid is invalid".format(row.get("dcc_uuid"))
            assert is_valid_uuid(row.get("bmv_subnet_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
            assert is_valid_uuid(row.get("bmv_vpc_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
            assert row.get("update_pending")==False, "nexthop {} still pending".format(row.get("dcc_uuid"))
        else:
            count2 = count2+1
            assert not is_valid_uuid(row.get("bmv_next_hop_uuid")), "nic {} uuid is invalid".format(row.get("dcc_uuid"))
            assert not is_valid_uuid(row.get("bmv_subnet_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
            assert not is_valid_uuid(row.get("bmv_vpc_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
            assert row.get("update_pending")==True, "nexthop {} still pending".format(row.get("dcc_uuid"))

    assert count1==16
    assert count2==2

    res_list= test_dao.get_table("bmv_dmac_fanout")
    count1 = 0
    count2 = 0
    for row in res_list:
        if row.get("fc_dpu_id_local") != dpu_id_offline:
            count1 = count1+1
            assert is_valid_uuid(row.get("bmv_dmac_uuid")), "nic {} uuid is {} invalid".format(row.get("dcc_uuid"), row.get("bmv_dmac_uuid"))
            assert is_valid_uuid(row.get("bmv_next_hop_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
            assert is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
            assert row.get("update_pending")==False, "dmac {}/{} still pending".format(row.get("dcc_network_uuid"), row.get("mac"))
        else:
            count2 = count2+1
            assert not is_valid_uuid(row.get("bmv_dmac_uuid")), "nic {} uuid is {} invalid".format(row.get("dcc_uuid"), row.get("bmv_dmac_uuid"))
            assert not is_valid_uuid(row.get("bmv_next_hop_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
            assert not is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
            assert row.get("update_pending")==True, "dmac {}/{} still pending".format(row.get("dcc_network_uuid"), row.get("mac"))

    assert count1==16
    assert count2==0

    # heal DPU
    test_dao.set_dpus_available()

    #re-test
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()


    res_list= test_dao.get_table("bmv_vpc_fanout")
    count1 = 0
    for row in res_list:
        count1 = count1+1
        assert is_valid_uuid(row.get("bmv_vpc_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "vpc {} still pending".format(row.get("dcc_uuid"))
    assert count1==11


    res_list= test_dao.get_table("bmv_subnet_fanout")
    count1 = 0

    for row in res_list:
        count1 = count1+1
        assert is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_vpc_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "subnet {} still pending".format(row.get("dcc_uuid"))
    assert count1==11

    res_list= test_dao.get_table("bmv_nic")
    count1 = 0
    for row in res_list:
        count1 = count1+1
        assert is_valid_uuid(row.get("bmv_nic_uuid")), "nic {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_vpc_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "nic {} still pending".format(row.get("dcc_uuid"))
    assert count1==11

    res_list= test_dao.get_table("bmv_next_hop_fanout")
    count1 = 0
    for row in res_list:
        count1 = count1+1
        assert is_valid_uuid(row.get("bmv_next_hop_uuid")), "nic {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_subnet_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_vpc_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "nexthop {} still pending".format(row.get("dcc_uuid"))
    assert count1==20

    res_list= test_dao.get_table("bmv_dmac_fanout")
    count1 = 0
    for row in res_list:
        count1 = count1+1
        assert is_valid_uuid(row.get("bmv_dmac_uuid")), "nic {} uuid is {} invalid".format(row.get("dcc_uuid"), row.get("bmv_dmac_uuid"))
        assert is_valid_uuid(row.get("bmv_next_hop_uuid")), "vpc {} uuid is invalid".format(row.get("dcc_uuid"))
        assert is_valid_uuid(row.get("bmv_subnet_uuid")), "subnet {} uuid is invalid".format(row.get("dcc_uuid"))
        assert row.get("update_pending")==False, "dmac {}/{} still pending".format(row.get("dcc_network_uuid"), row.get("mac"))
    assert count1==20

@pytest.mark.usefixtures('populate_database')
def test_sync_mactable(mock_api_client, test_dao):
    #Logging.setup(_FULL_LOGGING);
    sync = BmvSynchronizer(test_dao)
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',1)]
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        assert row.get("dcc_nic_uuid")=='aa9ce4f2-1d4f-11eb-adc1-0242ac120002'
        assert row.get("mac")=="77:77:77:77:77:77"
        assert row.get("fc_dpu_id")=="99:99:99:99:99:01"
        assert row.get("refresh_pending")==False
    assert count==1
    res_list= test_dao.get_table("bmv_dmac_fanout")
    count = 0
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
            assert row.get("fc_dpu_id_remote") == '99:99:99:99:99:01'
            assert row.get("delete_pending") == False
            assert row.get("update_pending") == True
            assert row.get("learned") == True
        else:
            assert row.get("learned") == False
    assert count==2
    # sync DMAC make sure that new entries are still there
    sync.process_dmac_sync()
    count = 0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
            assert row.get("fc_dpu_id_remote") == '99:99:99:99:99:01'
            assert row.get("delete_pending") == False
            assert row.get("update_pending") == False
            assert row.get("learned") == True
        else:
            assert row.get("learned") == False
    assert count==2

    count = 0
    res_list= test_dao.get_table("bmv_mac_tbl")
    for row in res_list:
        count = count+1
        assert row.get("refresh_pending") == False
        assert row.get("migrated") == False
        print(row)
    assert count==1

    # erase learned mac, make sure it is and  DMAC is deleted
    mock_api_client.learned_mac_entries = []
    #import pdb; pdb.set_trace()
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        assert row.get("refresh_pending") == True
        assert row.get("migrated") == False
    assert count==1
    sync.process_dmac_sync()
    count = 0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
    assert count==2

    #prepare to expire
    test_dao.exec_query_noreturn("UPDATE networking.bmv_mac_tbl set last_update_time=NOW() - INTERVAL '5 hours'")
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        print(row)
    assert count==0
    sync.process_dmac_sync()
    count = 0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
    assert count==0


@pytest.mark.usefixtures('populate_database')
def test_events_mactable(mock_api_client, test_dao):
    #Logging.setup(_FULL_LOGGING);
    sync = BmvSynchronizer(test_dao)
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',1)]
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()
    #test_dao.dump_query("select * from networking.bmv_dmac_fanout")
    #import pdb; pdb.set_trace()
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()

    event = MacEvent(dpu_id='99:99:99:99:99:01',
                     nic_uuid='aa9ce4f2-1d4f-11eb-adc1-0242ac120002',
                     mac='77:77:77:77:77:78',
                     vlan=11,
                     sequence_number=2,
                     is_delete = False)
    sync.process_event(event)
    sync.erase_stale_macs()
    sync.process_dmac_sync()

    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        assert row.get("dcc_nic_uuid")=='aa9ce4f2-1d4f-11eb-adc1-0242ac120002'
        assert row.get("mac") in ["77:77:77:77:77:77", "77:77:77:77:77:78"]
        assert row.get("fc_dpu_id")=="99:99:99:99:99:01"
        assert row.get("refresh_pending")==False
    assert count==2
    #test_dao.dump_query(QQQ)
    #import pdb; pdb.set_trace()
    res_list= test_dao.get_table("bmv_dmac_fanout")
    count = 0
    for row in res_list:
        if row.get("mac") in  ["77:77:77:77:77:77", "77:77:77:77:77:78"]:
            count = count+1
            assert row.get("fc_dpu_id_remote") == '99:99:99:99:99:01'
            assert row.get("delete_pending") == False
            assert row.get("update_pending") == False
            assert row.get("learned") == True
        else:
            assert row.get("learned") == False
    assert count==4

    #add nic on another server
    test_dao.exec_query_noreturn('''INSERT INTO networking.network_nic VALUES ('4cbfdb54-7b74-4689-9c56-38317c8e859e', 'nic1-4', '11:11:11:11:11:04', 'up', False, '20e39ae6-1d52-11eb-adc1-0242ac120002', '34ede854-1d4b-11eb-adc1-0242ac120002', 2)''');
    # run through all sybchronization steps
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()

    res_list= test_dao.get_table("bmv_dmac_fanout")
    count = 0
    for row in res_list:
        if row.get("mac") in  ["77:77:77:77:77:77", "77:77:77:77:77:78"]:
            count = count+1
            assert row.get("fc_dpu_id_remote") == '99:99:99:99:99:01'
            assert row.get("delete_pending") == False
            assert row.get("update_pending") == False
            assert row.get("learned") == True
        else:
            assert row.get("learned") == False
    assert count==6

    # erase learned mac, make sure it is and  DMAC is deleted
    event = MacEvent(dpu_id='99:99:99:99:99:01',
                     nic_uuid='aa9ce4f2-1d4f-11eb-adc1-0242ac120002',
                     mac='77:77:77:77:77:77',
                     vlan=11,
                     sequence_number=1,
                     is_delete = True)
    sync.process_event(event)
    sync.process_dmac_sync()
    sync.erase_stale_macs()
    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        if row.get("mac") == '77:77:77:77:77:77':
            assert row.get("refresh_pending") == True
            assert row.get("migrated") == False
        elif row.get("mac") == '77:77:77:77:77:78':
            assert row.get("refresh_pending") == False
            assert row.get("migrated") == False
        else:
            assert False
    assert count==2
    sync.process_dmac_sync()
    count = 0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    # record is not deleted until timeout expire
    for row in res_list:
        if row.get("mac") in ["77:77:77:77:77:77","77:77:77:77:77:78"]:
            count = count+1
    assert count==6
    #remove NIC
    test_dao.exec_query_noreturn('''DELETE FROM networking.network_nic where name='nic1-4';''');
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()
    sync.erase_stale_macs()
    count=0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") in ["77:77:77:77:77:77","77:77:77:77:77:78"]:
            count = count+1
    assert count==4


@pytest.mark.usefixtures('populate_database')
def test_nicdeleted_mactable(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',1)]
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()
    #test_dao.dump_query("select * from networking.bmv_dmac_fanout")
    #import pdb; pdb.set_trace()
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()

    res_list = test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        assert row.get("dcc_nic_uuid")=='aa9ce4f2-1d4f-11eb-adc1-0242ac120002'
        assert row.get("mac")=="77:77:77:77:77:77" or row.get("mac")=="77:77:77:77:77:78"
        assert row.get("fc_dpu_id")=="99:99:99:99:99:01"
        assert row.get("refresh_pending")==False
    assert count==1
    res_list= test_dao.get_table("bmv_dmac_fanout")
    count = 0
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
            assert row.get("fc_dpu_id_remote") == '99:99:99:99:99:01'
            assert row.get("delete_pending") == False
            assert row.get("update_pending") == True
            assert row.get("learned") == True
        else:
            assert row.get("learned") == False
    assert count==2
    # sync DMAC make sure that new entries are still there
    sync.process_dmac_sync()
    count = 0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
            assert row.get("fc_dpu_id_remote") == '99:99:99:99:99:01'
            assert row.get("delete_pending") == False
            assert row.get("update_pending") == False
            assert row.get("learned") == True
        else:
            assert row.get("learned") == False
    assert count==2

    count = 0
    res_list= test_dao.get_table("bmv_mac_tbl")
    for row in res_list:
        count = count+1
        assert row.get("refresh_pending") == False
        assert row.get("migrated") == False
    assert count==1

    test_dao.exec_query_noreturn("DELETE FROM networking.network_nic WHERE uuid='aa9ce4f2-1d4f-11eb-adc1-0242ac120002' RETURNING *;")

    # erase learned mac and nic make sure it is deleted
    mock_api_client.learned_mac_entries = []

    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()

    #test_dao.dump_query("select * from networking.network_nic")
    #test_dao.dump_query("select * from networking.bmv_dmac_fanout")

    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
    assert count==0
    sync.process_dmac_sync()
    count = 0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            assert row.get("delete_pending")
            count = count+1
    assert count==0


@pytest.mark.usefixtures('populate_database')
def test_migrations_mactable(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',1)]
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()
    #test_dao.dump_query("select * from networking.bmv_dmac_fanout")
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    sync.process_dmac_sync()

    #prepare to migrate

    test_dao.exec_query_noreturn("UPDATE networking.bmv_mac_tbl set last_update_time=NOW() - INTERVAL '2m'")
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'3f8e0744-1d50-11eb-adc1-0242ac120002',2)]
    sync.process_mactbl_sync('99:99:99:99:99:02')
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',1)]
    sync.process_mactbl_sync('99:99:99:99:99:01')

    #prepare to recieve batch of updates
    mock_api_client.call_record = []
    sync.erase_stale_macs()
    #print("CALLS={}".format(mock_api_client.call_record))
    mac_deletes = mock_api_client.find_api_calls("DELETE", "/network/dpus/{dpu_id}/bmv_mactbl/{bmv_mac_seq_num}")
    assert len(mac_deletes) == 1
    assert mac_deletes[0]["path_params"]["dpu_id"] == '99:99:99:99:99:01'
    assert mac_deletes[0]["path_params"]['bmv_mac_seq_num'] == 1

    sync.process_dmac_sync()
    #test_dao.dump_query("select * from networking.bmv_mac_tbl")

    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        if row.get("fc_dpu_id")=='99:99:99:99:99:01':
            assert False, "First MAC should be deleted by now"
        elif row.get("fc_dpu_id")=='99:99:99:99:99:02':
            assert row.get("refresh_pending") == False
            assert row.get("migrated") == False
        else:
            assert False, "Unexpected row {}".format(row)
    assert count==1
    count = 0


    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
            assert row.get("fc_dpu_id_remote")=='99:99:99:99:99:02'
    assert count==2

    # run again with both entries still there
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'3f8e0744-1d50-11eb-adc1-0242ac120002',2)]
    sync.process_mactbl_sync('99:99:99:99:99:02')
    sync.erase_stale_macs()
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',3)]
    sync.process_mactbl_sync('99:99:99:99:99:01')
    mock_api_client.call_record = []
    sync.erase_stale_macs()
    # find delete Intent API callse
    mac_deletes = mock_api_client.find_api_calls("DELETE", "/network/dpus/{dpu_id}/bmv_mactbl/{bmv_mac_seq_num}")
    assert len(mac_deletes) == 1
    assert mac_deletes[0]["path_params"]["dpu_id"]=='99:99:99:99:99:02'
    assert mac_deletes[0]["path_params"]["bmv_mac_seq_num"] == 2

    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        if row.get("fc_dpu_id")=='99:99:99:99:99:01':
            assert row.get("refresh_pending") == False
            assert row.get("migrated") == False
        elif row.get("fc_dpu_id")=='99:99:99:99:99:02':
            assert "Second MAC should be deleted by now"
        else:
            assert False, "Unexpected row {}".format(row)
    assert count==1
    sync.process_dmac_sync()
    count=0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
            assert row.get("fc_dpu_id_remote")=='99:99:99:99:99:01'
    assert count==2


@pytest.mark.usefixtures('populate_database')
def test_migrations_events_mactable(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',1)]
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()
    #test_dao.dump_query("select * from networking.bmv_dmac_fanout")
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    sync.process_dmac_sync()

    #prepare to migrate
    test_dao.exec_query_noreturn("UPDATE networking.bmv_mac_tbl set last_update_time=NOW() - INTERVAL '2m'")


    event = MacEvent(dpu_id='99:99:99:99:99:02',
                     nic_uuid='3f8e0744-1d50-11eb-adc1-0242ac120002',
                     mac='77:77:77:77:77:77',
                     vlan=11,
                     sequence_number=2,
                     is_delete = False)
    sync.process_event(event)

    #prepare to recieve batch of updates
    mock_api_client.call_record = []
    sync.erase_stale_macs()
    #print("CALLS={}".format(mock_api_client.call_record))
    mac_deletes = mock_api_client.find_api_calls("DELETE", "/network/dpus/{dpu_id}/bmv_mactbl/{bmv_mac_seq_num}")
    assert len(mac_deletes) == 1
    assert mac_deletes[0]["path_params"]["dpu_id"] == '99:99:99:99:99:01'
    assert mac_deletes[0]["path_params"]['bmv_mac_seq_num'] == 1

    sync.process_dmac_sync()
    #test_dao.dump_query("select * from networking.bmv_mac_tbl")

    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        if row.get("fc_dpu_id")=='99:99:99:99:99:01':
            assert False, "First MAC should be deleted by now"
        elif row.get("fc_dpu_id")=='99:99:99:99:99:02':
            assert row.get("refresh_pending") == False
            assert row.get("migrated") == False
        else:
            assert False, "Unexpected row {}".format(row)
    assert count==1
    count = 0


    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
            assert row.get("fc_dpu_id_remote")=='99:99:99:99:99:02'
    assert count==2


    # add event for first mac back
    mock_api_client.call_record = []
    event = MacEvent(dpu_id='99:99:99:99:99:01',
                     nic_uuid='aa9ce4f2-1d4f-11eb-adc1-0242ac120002',
                     mac='77:77:77:77:77:77',
                     vlan=11,
                     sequence_number=3,
                     is_delete = False)
    sync.process_event(event)
    sync.erase_stale_macs()
    # find delete Intent API callse
    mac_deletes = mock_api_client.find_api_calls("DELETE", "/network/dpus/{dpu_id}/bmv_mactbl/{bmv_mac_seq_num}")
    assert len(mac_deletes) == 1
    assert mac_deletes[0]["path_params"]["dpu_id"]=='99:99:99:99:99:02'
    assert mac_deletes[0]["path_params"]["bmv_mac_seq_num"] == 2

    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        if row.get("fc_dpu_id")=='99:99:99:99:99:01':
            assert row.get("refresh_pending") == False
            assert row.get("migrated") == False
        elif row.get("fc_dpu_id")=='99:99:99:99:99:02':
            assert "Second MAC should be deleted by now"
        else:
            assert False, "Unexpected row {}".format(row)
    assert count==1
    sync.process_dmac_sync()
    count=0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
            assert row.get("fc_dpu_id_remote")=='99:99:99:99:99:01'
    assert count==2


@pytest.mark.usefixtures('populate_database')
def test_rediscovery_mactable(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',8)]
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()
    #test_dao.dump_query("select * from networking.bmv_dmac_fanout")
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    sync.process_dmac_sync()
    dmac_uuids = []
    first_update_time = None

    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        if row.get("fc_dpu_id")=='99:99:99:99:99:01':
            assert row.get("refresh_pending") == False
            first_update_time = row.get("first_update_time")
        else:
            assert False, "Unexpected row {}".format(row)
    assert count==1

    count = 0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            dmac_uuids.append(row.get("bmv_dmac_uuid"))
            count = count+1
    assert count==2


    #prepare to expire
    mock_api_client.learned_mac_entries = []
    test_dao.exec_query_noreturn("UPDATE networking.bmv_mac_tbl set last_update_time=NOW() - INTERVAL '5m'")
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    sync.process_dmac_sync()


    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        if row.get("fc_dpu_id")=='99:99:99:99:99:01':
            assert row.get("refresh_pending") == True
            assert row.get("first_update_time") == first_update_time
        else:
            assert False, "Unexpected row {}".format(row)
    assert count==1
    sync.process_dmac_sync()
    count = 0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
            assert row.get("fc_dpu_id_remote")=='99:99:99:99:99:01'
            assert row.get("bmv_dmac_uuid") in dmac_uuids
    assert count==2

    #now rediscover
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',9)]
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    sync.process_dmac_sync()

    # two times to rediscover
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    sync.process_dmac_sync()

    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        if row.get("fc_dpu_id")=='99:99:99:99:99:01':
            assert row.get("refresh_pending") == False
            assert row.get("first_update_time") == first_update_time
        else:
            assert False, "Unexpected row {}".format(row)
    assert count==1

    count = 0
    res_list= test_dao.get_table("bmv_dmac_fanout")
    for row in res_list:
        if row.get("mac") == "77:77:77:77:77:77":
            count = count+1
            assert row.get("fc_dpu_id_remote")=='99:99:99:99:99:01'
            assert row.get("bmv_dmac_uuid") in dmac_uuids
    assert count==2

@pytest.mark.usefixtures('populate_database')
def test_erase_stale_mac_entries(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',1),("88:88:88:88:88:88",'3f8e0744-1d50-11eb-adc1-0242ac120002',2)]
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()

    sync.process_mactbl_sync('99:99:99:99:99:01')
    test_dao.dump_query("select * from networking.bmv_mac_tbl")

    sync.erase_stale_macs()
    sync.process_dmac_sync()
    dmac_uuids = []
    first_update_time = None

    res_list= test_dao.get_table("bmv_mac_tbl")
    count = 0
    for row in res_list:
        count = count+1
        dpu_id = row.get("fc_dpu_id")
        if dpu_id=='99:99:99:99:99:01' or dpu_id=='99:99:99:99:99:02':
            assert row.get("refresh_pending") == False
        else:
            assert False, "Unexpected row {}".format(row)
    assert count==2


    # remove one of the nics
    test_dao.exec_query_noreturn(
        "DELETE FROM networking.network_nic WHERE uuid='aa9ce4f2-1d4f-11eb-adc1-0242ac120002' RETURNING *;")
    sync.process_nic_sync()

    sync.erase_stale_macs()

    #should have only one mac record remaining
    res_list = test_dao.get_table("bmv_mac_tbl")
    count = sum(1 for x in res_list)
    assert count == 1
    for row in res_list:
        assert row.get("fc_dpu_id")=='99:99:99:99:99:02'


@pytest.mark.usefixtures('populate_database')
def test_sync_with_gw(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    #add GW DPU
    test_dao.exec_query_noreturn("INSERT INTO networking.dpu_cache VALUES ('566c5a8c-8f42-4293-b269-21d2d38a526f', '11:12:13:22:23:24', '12.13.14.15', 'cb0e5ba0-6681-4b0e-9a83-b627f5d925bb', True, 'gw') ;")

    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()

    count_next_hop1=next(test_dao.exec_query("select COUNT(*) as val from networking.bmv_next_hop_fanout;"))["val"]
    count_dmac1 =next(test_dao.exec_query("select COUNT(*) as val from networking.bmv_dmac_fanout;"))["val"]

    test_dao.exec_query_noreturn(
        "INSERT into networking.bmv_nic (dcc_nic_uuid, dcc_dpu_uuid, dcc_network_uuid, bmv_vpc_uuid, dcc_vrf_uuid,  bmv_subnet_uuid, macaddress, hu, controller, pf, vf, delete_pending, update_pending) "
        "(SELECT '33333333-1d4f-11eb-adc1-0242ac120002', dpu_cache.dcc_uuid, network.uuid,'33333333-1d4f-11eb-adc1-0242ac120002' , vrf.uuid, '33333333-1d4f-11eb-adc1-0242ac120002', '33:33:33:11:11:11', -1, -1, -1, -1, False, True "
        "FROM  networking.network network, networking.dpu_cache dpu_cache,  networking.vrf vrf,  networking.cidr_block cidr_block "
        "WHERE vrf.uuid=cidr_block.vrf_uuid and network.cidr_block_uuid=cidr_block.uuid and network.name='net1' and dpu_cache.model='gw' ) "
    )

    #test_dao.dump_query("select * from networking.dpu_cache")
    #test_dao.dump_query("select * from networking.bmv_nic")

    mock_api_client.counter_methods = {}
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()

    count_next_hop2=next(test_dao.exec_query("select COUNT(*) as val from networking.bmv_next_hop_fanout;"))["val"]
    count_dmac2 =next(test_dao.exec_query("select COUNT(*) as val from networking.bmv_dmac_fanout;"))["val"]
    assert count_next_hop2 == (count_next_hop1+3)
    assert count_dmac2 == (count_dmac1+3)
    assert mock_api_client.counter_methods=={"POST":6}


@pytest.mark.usefixtures('populate_database')
def test_sync_tobgp(mock_api_client, test_dao):
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',1),("11:11:11:11:11:01",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',2)]
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    sync.process_dmac_sync()

    count_dpu = next(test_dao.exec_query("select COUNT(*) as val from networking.dpu_cache;"))["val"]
    assert count_dpu == 9

    mac_count = next(test_dao.exec_query("select COUNT(*) as val from networking.bmv_mac_tbl;"))["val"]
    assert mac_count == 2

    sync.process_bmv_macs_to_bgp_sync()
    count_bgp_routes = next(test_dao.exec_query("select COUNT(*) as val from networking.bgp_route;"))["val"]
    assert count_bgp_routes == 12



@pytest.mark.usefixtures('populate_database')
def test_sync_frombgp(mock_api_client, test_dao):
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()

    count_dpu = next(test_dao.exec_query("select COUNT(*) as val from networking.dpu_cache;"))["val"]
    assert count_dpu == 9

    count_next_hop = next(test_dao.exec_query("select COUNT(*) as val from networking.bmv_next_hop_fanout;"))["val"]
    assert count_next_hop == 20

    count_dmac = next(test_dao.exec_query("select COUNT(*) as val from networking.bmv_dmac_fanout;"))["val"]
    assert count_dmac == 20

    test_dao.exec_query_noreturn("INSERT INTO networking.bgp_route VALUES (NULL, '65001:01', 11111, '44:44:44:44:44:44', '77.11.23.34', '71.11.21.1', 'bgp', FALSE, FALSE)")
    test_dao.exec_query_noreturn("INSERT INTO networking.bgp_route VALUES (NULL, '65001:01', 22222, '44:44:44:44:44:45', '77.11.23.35', '71.11.21.5', 'bgp', FALSE, FALSE)")

    sync.process_bgp_sync()

    count_dpu = next(test_dao.exec_query("select COUNT(*) as val from networking.dpu_cache;"))["val"]
    assert count_dpu == 11

    count_next_hop = next(test_dao.exec_query("select COUNT(*) as val from networking.bmv_next_hop_fanout;"))["val"]
    assert count_next_hop == 26

    count_dmac = next(test_dao.exec_query("select COUNT(*) as val from networking.bmv_dmac_fanout;"))["val"]
    assert count_dmac == 26

@pytest.mark.usefixtures('populate_database')
def test_bgp_sync(mock_api_client, test_dao, xmppMockServer):

    class BgpConfig(Config):
        def __init__(self):
            self.xmppPort = 5222
            self.local_as = 6001
            self.remote_as = 6002
            self.local_ip = "10.1.1.1"
            self.remote_ip = "10.1.1.3"
            self.config_folder = "/"
            self.poll_rate = 1.0

    class FakeBmvLoop:
        def __init__(self):
            self.ev_endofrib = 0
        def event_bgp_rib_ready(self):
            self.ev_endofrib += 1

    sim_bmv_loop = FakeBmvLoop()
    xmpp_client = XmppClient(sim_bmv_loop, BgpConfig(),  test_dao)
    mock_api_client.learned_mac_entries = [("77:77:77:77:77:77",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',1),("11:11:11:11:11:01",'aa9ce4f2-1d4f-11eb-adc1-0242ac120002',2)]
    sync = BmvSynchronizer(test_dao)
    sync.process_vpc_sync()
    sync.process_subnet_sync()
    sync.process_nic_sync()
    sync.process_nexthop_sync()
    sync.process_dmac_sync()
    sync.process_mactbl_sync('99:99:99:99:99:01')
    sync.erase_stale_macs()
    sync.process_dmac_sync()
    xmpp_client.start()
    sync.process_bgp_sync()
    count_bgp_routes = next(test_dao.exec_query("select COUNT(*) as val from networking.bgp_route;"))["val"]
    assert count_bgp_routes == 12

    test_dao.dump_query("select * from networking.vrf")

    test_dao.dump_query(GET_BGP_ROUTE_PENDING)

    xmpp_client.signal_db_change()
    time.sleep(15)
    prev_recv_len =0;
    # poll until xmpp client is done
    while len(xmppMockServer.recv_data) != prev_recv_len:
        prev_recv_len = len(xmppMockServer.recv_data)
        time.sleep(5)

    xmpp_client.stopThread = True
    xmpp_client.join(2)
    assert sim_bmv_loop.ev_endofrib == 1

    assert not xmpp_client.exc, "xmpp exception: {}".format(xmpp_client.exc)

    # vrf/mac/vxlan
    # initstream + subscribe-vrf1 + subscribe-vrf2
    # vrf-1/11:11:11:11:33:03/33333 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/33333 + collect
    # vrf-1/11:11:11:11:33:02/33333 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/33333 + collect
    # vrf-1/11:11:11:11:33:01/33333 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/33333 + collect
    # vrf-1/11:11:11:11:22:03/22222 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/22222 + collect
    # vrf-1/11:11:11:11:22:02/22222 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/22222 + collect
    # vrf-1/11:11:11:11:22:01/22222 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/22222 + collect
    # vrf-1/11:11:11:11:11:03/11111 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/11111 + collect
    # vrf-1/11:11:11:11:11:02/11111 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/11111 + collect
    # vrf-1/11:11:11:11:11:01/11111 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/11111 + collect
    # vrf-1/77:77:77:77:77:77/11111 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/11111 + collect
    # vrf-2/11:11:11:11:33:04/44444 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/44444 + collect
    # vrf-2/11:11:11:11:33:03/44444 + collect
    # vrf-1/ff:ff:ff:ff:ff:ff,0.0.0.0/44444 + collect
    # total 51
    assert len(xmppMockServer.recv_data) == 51, "recv={}.".format(xmppMockServer.recv_data)

    tree = ET.parse("/config.xml")
    root = tree.getroot()
    assert root.tag == "config"
    assert len(root.findall("bgp-router"))==2
    assert len(root.findall("routing-instance")) == 2
    assert len(root.findall("virtual-network")) == 2

    xmpp_client.stopThread = True
    xmppMockServer.server_close()
    xmppMockServer.shutdown()
    xmpp_client.join(2)
