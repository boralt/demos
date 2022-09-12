#######################################################################
# FUNGIBLE, INC. CONFIDENTIAL AND PROPRIETARY
#
# Copyright (C) 2019 by Fungible, Inc.
# This work is the property of Fungible, Inc. (Company).
#
# It contains proprietary information and trade secrets of Company.
# Disclosure, use, or reproduction without the prior written approval
# of Company is prohibited. All rights reserved.
#######################################################################


# -------vpc-------
SYNC_VPC_UPDATES = (
    "INSERT INTO networking.bmv_vpc_fanout (dcc_uuid, fc_dpu_id, bmv_vpc_uuid, route_target, delete_pending, update_pending) "
    "(SELECT DISTINCT ON (vrf.uuid, dpu_cache.fc_dpu_id) vrf.uuid , dpu_cache.fc_dpu_id, NULL, '0000' ,   False, False "
    " FROM networking.vrf as vrf, networking.dpu_cache as dpu_cache, networking.network  network, networking.cidr_block  cidr_block, networking.network_nic network_nic "
    "WHERE vrf.uuid=cidr_block.vrf_uuid and cidr_block.uuid=network.cidr_block_uuid and network.uuid=network_nic.network_uuid and network_nic.server_uuid=dpu_cache.server_uuid) "
    "ON CONFLICT ( dcc_uuid, fc_dpu_id) DO UPDATE SET route_target=EXCLUDED.route_target;"
)

GET_VPC_PENDING = (
    "SELECT  bmv_vpc_fanout.dcc_uuid as dcc_uuid, bmv_vpc_fanout.fc_dpu_id as fc_dpu_id, vrf.vrf_id as vrf_id, dpu_cache.model as model FROM networking.bmv_vpc_fanout bmv_vpc_fanout, networking.dpu_cache dpu_cache, networking.vrf vrf WHERE bmv_vpc_fanout.update_pending=True and bmv_vpc_fanout.delete_pending=False and dpu_cache.fc_dpu_id=bmv_vpc_fanout.fc_dpu_id and dpu_cache.online=TRUE and vrf.uuid=bmv_vpc_fanout.dcc_uuid"
)

GET_VPC_DELETED = (
    "SELECT  bmv_vpc_fanout.dcc_uuid as dcc_uuid, bmv_vpc_fanout.bmv_vpc_uuid as bmv_vpc_uuid, bmv_vpc_fanout.fc_dpu_id as fc_dpu_id,  dpu_cache.model as model FROM networking.bmv_vpc_fanout bmv_vpc_fanout, networking.dpu_cache dpu_cache WHERE bmv_vpc_fanout.delete_pending=True and dpu_cache.fc_dpu_id=bmv_vpc_fanout.fc_dpu_id ;"
)

SET_VPC_PLACED = (
    "UPDATE networking.bmv_vpc_fanout SET bmv_vpc_uuid='{}', update_pending=False WHERE dcc_uuid='{}' and fc_dpu_id='{}' RETURNING bmv_vpc_uuid"
)

SYNC_VPC_DELETE = (
    "UPDATE networking.bmv_vpc_fanout SET delete_pending=TRUE WHERE NOT EXISTS (SELECT 1 FROM networking.vrf WHERE networking.vrf.uuid=networking.bmv_vpc_fanout.dcc_uuid);"
)

SYNC_VPC_DELETE_IDLE = (
    "DELETE from networking.bmv_vpc_fanout WHERE NOT EXISTS (SELECT 1 FROM networking.vrf WHERE networking.vrf.uuid=networking.bmv_vpc_fanout.dcc_uuid) and networking.bmv_vpc_fanout.bmv_vpc_uuid is NULL;"
)

DELETE_VPC = (
    "DELETE FROM networking.bmv_vpc_fanout WHERE bmv_vpc_uuid='{}';"
)


#-------- subnet ------
SYNC_SUBNET_UPDATES = (
    "INSERT into networking.bmv_subnet_fanout (dcc_uuid, fc_dpu_id, bmv_vpc_uuid, dcc_vrf_uuid, gateway, vlan_id, vxlan_id, delete_pending, update_pending) "
    "(SELECT DISTINCT ON (network.uuid, dpu_cache.fc_dpu_id) network.uuid, dpu_cache.fc_dpu_id, bmv_vpc_fanout.bmv_vpc_uuid, bmv_vpc_fanout.dcc_uuid, network.gateway, network.vlan_id, network.vxlan_id, False, True "
    "FROM networking.network network, networking.dpu_cache dpu_cache, networking.cidr_block cidr_block, networking.bmv_vpc_fanout bmv_vpc_fanout, networking.network_nic network_nic "
    "WHERE network.uuid=network_nic.network_uuid and network_nic.server_uuid=dpu_cache.server_uuid and cidr_block.vrf_uuid=bmv_vpc_fanout.dcc_uuid and network.cidr_block_uuid=cidr_block.uuid and bmv_vpc_fanout.fc_dpu_id=dpu_cache.fc_dpu_id) "
    "ON CONFLICT ( dcc_uuid, fc_dpu_id) DO UPDATE SET gateway=EXCLUDED.gateway, vlan_id=EXCLUDED.vlan_id, vxlan_id=EXCLUDED.vxlan_id, bmv_vpc_uuid=EXCLUDED.bmv_vpc_uuid ;"
)

GET_SUBNET_PENDING = (
    "SELECT  bmv_subnet_fanout.dcc_uuid as dcc_uuid, bmv_subnet_fanout.fc_dpu_id as fc_dpu_id, bmv_subnet_fanout.bmv_vpc_uuid as bmv_vpc_uuid, bmv_subnet_fanout.dcc_vrf_uuid,  bmv_subnet_fanout.gateway as gateway, bmv_subnet_fanout.vlan_id as vlan_id, bmv_subnet_fanout.vxlan_id as vxlan_id, dpu_cache.model as model "
    "FROM networking.bmv_subnet_fanout bmv_subnet_fanout, networking.dpu_cache dpu_cache "
    "WHERE bmv_subnet_fanout.update_pending=True and  bmv_subnet_fanout.delete_pending=False and dpu_cache.fc_dpu_id=bmv_subnet_fanout.fc_dpu_id and dpu_cache.online=TRUE "
)

GET_SUBNET_DELETED = (
    "SELECT  bmv_subnet_fanout.dcc_uuid as dcc_uuid, bmv_subnet_fanout.bmv_subnet_uuid as bmv_subnet_uuid,  bmv_subnet_fanout.fc_dpu_id as fc_dpu_id,  dpu_cache.model as model "
    "FROM networking.bmv_subnet_fanout bmv_subnet_fanout, networking.dpu_cache dpu_cache "
    "WHERE bmv_subnet_fanout.delete_pending=True and dpu_cache.fc_dpu_id=bmv_subnet_fanout.fc_dpu_id and dpu_cache.online=TRUE "
)


SET_SUBNET_PLACED = (
    "UPDATE networking.bmv_subnet_fanout SET bmv_subnet_uuid='{}', update_pending=False where dcc_uuid='{}' and fc_dpu_id='{}' RETURNING bmv_subnet_uuid"
)

SYNC_SUBNET_DELETE = (
    "UPDATE networking.bmv_subnet_fanout SET delete_pending=TRUE WHERE NOT EXISTS (SELECT 1 FROM networking.network WHERE networking.network.uuid=networking.bmv_subnet_fanout.dcc_uuid)"
)

SYNC_SUBNET_DELETE_IDLE = (
    "DELETE FROM networking.bmv_subnet_fanout WHERE NOT EXISTS (SELECT 1 FROM networking.network WHERE networking.network.uuid=networking.bmv_subnet_fanout.dcc_uuid) AND networking.bmv_subnet_fanout.bmv_subnet_uuid is NULL"
)

DELETE_SUBNET = (
    "DELETE FROM networking.bmv_subnet_fanout WHERE bmv_subnet_uuid='{}';"
)

ADD_SUBNET_ON_GW = (
    "INSERT INTO networking.bmv_nic (dcc_nic_uuid, dcc_dpu_uuid, dcc_network_uuid, bmv_vpc_uuid, dcc_vrf_uuid,  bmv_subnet_uuid, macaddress, hu, controller, pf, vf, delete_pending, update_pending) "
    "(SELECT '{0}', dpu_cache.dcc_uuid, '{1}','{3}' , vrf.uuid, '{3}', '{2}', -1, -1, -1, -1, False, True "
    "FROM  networking.network network, networking.dpu_cache dpu_cache,  networking.vrf vrf,  networking.cidr_block cidr_block "
    "WHERE vrf.uuid=cidr_block.vrf_uuid and network.cidr_block_uuid=cidr_block.uuid and network.uuid='{1}' and dpu_cache.model='gw' and dpu_cache.fc_dpu_id='{4}') RETURNING dcc_nic_uuid;"
)

DELETE_SUBNET_ON_GW = (
    "DELETE FROM networking.bmv_nic WHERE dcc_network_uuid='{}' and bmv_vpc_uuid='{}';"
)


#----------nic-----------

SYNC_NIC_UPDATES = (
    "INSERT into networking.bmv_nic (dcc_nic_uuid, dcc_dpu_uuid, dcc_network_uuid, bmv_vpc_uuid, dcc_vrf_uuid,  bmv_subnet_uuid, macaddress, hu, controller, pf, vf, delete_pending, update_pending) "
    "(SELECT DISTINCT ON (network_nic.uuid) network_nic.uuid, dpu_cache.dcc_uuid, network_nic.network_uuid,  bmv_subnet_fanout.bmv_vpc_uuid, bmv_vpc_fanout.dcc_uuid,  bmv_subnet_fanout.bmv_subnet_uuid, network_nic.mac_addr, 1, 0, (network_nic.slot%%2)+1, network_nic.slot, False, True "
    "FROM networking.network_nic network_nic, networking.network network, networking.dpu_cache dpu_cache, networking.bmv_vpc_fanout bmv_vpc_fanout, networking.cidr_block cidr_block, networking.bmv_subnet_fanout bmv_subnet_fanout "
    "WHERE network_nic.server_uuid=dpu_cache.server_uuid and network_nic.network_uuid=network.uuid and network.cidr_block_uuid=cidr_block.uuid and cidr_block.vrf_uuid=bmv_vpc_fanout.dcc_uuid and bmv_vpc_fanout.bmv_vpc_uuid=bmv_subnet_fanout.bmv_vpc_uuid and bmv_subnet_fanout.dcc_uuid=network_nic.network_uuid and bmv_subnet_fanout.fc_dpu_id=dpu_cache.fc_dpu_id and bmv_vpc_fanout.bmv_vpc_uuid IS NOT NULL ) "
    "ON CONFLICT (dcc_nic_uuid) DO UPDATE SET dcc_dpu_uuid=EXCLUDED.dcc_dpu_uuid, dcc_network_uuid=EXCLUDED.dcc_network_uuid, bmv_vpc_uuid=EXCLUDED.bmv_vpc_uuid, bmv_subnet_uuid=EXCLUDED.bmv_subnet_uuid,  macaddress=EXCLUDED.macaddress, hu=EXCLUDED.hu, controller=EXCLUDED.controller, pf=EXCLUDED.pf, vf=EXCLUDED.vf;"
)

GET_NIC_PENDING = (
    "SELECT  bmv_nic.dcc_nic_uuid as dcc_nic_uuid, dpu_cache.fc_dpu_id as fc_dpu_id, bmv_nic.bmv_nic_uuid as bmv_nic_uuid, bmv_nic.bmv_vpc_uuid as bmv_vpc_uuid, bmv_nic.macaddress as macaddress, bmv_nic.bmv_subnet_uuid as bmv_subnet_uuid, bmv_nic.hu as hu, bmv_nic.controller as controller, bmv_nic.pf as pf, bmv_nic.vf as vf, bmv_nic.dcc_dpu_uuid as dcc_dpu_uuid, bmv_nic.dcc_network_uuid as dcc_network_uuid, bmv_nic.dcc_vrf_uuid as dcc_vrf_uuid, dpu_cache.model as fc_model "
    "FROM networking.bmv_nic bmv_nic, networking.dpu_cache dpu_cache WHERE bmv_nic.update_pending=True and bmv_nic.delete_pending=False and dpu_cache.dcc_uuid=bmv_nic.dcc_dpu_uuid and dpu_cache.online=TRUE"
)

GET_GW_NIC_PENDING = (
    "SELECT COUNT(*) as v FROM networking.bmv_nic bmv_nic where bmv_nic.update_pending=True and bmv_nic.vf=-1"
)

GET_NIC_DELETED = (
    "SELECT bmv_nic.dcc_nic_uuid as dcc_nic_uuid, dpu_cache.fc_dpu_id as fc_dpu_id, bmv_nic.bmv_nic_uuid as bmv_nic_uuid, dpu_cache.model as model, bmv_nic.vf as vf "
    "FROM networking.bmv_nic bmv_nic, networking.dpu_cache dpu_cache WHERE bmv_nic.delete_pending=True and dpu_cache.dcc_uuid=bmv_nic.dcc_dpu_uuid and dpu_cache.online=TRUE"
)


SET_NIC_PLACED = (
    "UPDATE networking.bmv_nic SET bmv_nic_uuid='{}', update_pending=False, vf={} where dcc_nic_uuid='{}' RETURNING bmv_nic_uuid"
)

SYNC_NIC_DELETE = (
    "UPDATE networking.bmv_nic SET delete_pending=TRUE WHERE NOT EXISTS (SELECT 1 FROM networking.network_nic WHERE networking.network_nic.uuid=networking.bmv_nic.dcc_nic_uuid AND networking.network_nic.server_uuid IS NOT NULL) AND networking.bmv_nic.vf>-1"
)

SYNC_NIC_DELETE_IDLE = (
    "DELETE FROM networking.bmv_nic WHERE NOT EXISTS (SELECT 1 FROM networking.network_nic WHERE networking.network_nic.uuid=networking.bmv_nic.dcc_nic_uuid) AND networking.bmv_nic_uuid IS NULL AND networking.bmv_nic.vf>-1"
)


DELETE_NIC = (
    "DELETE FROM networking.bmv_nic WHERE bmv_nic_uuid='{}';"
)

FIND_FREE_VF = (
    "SELECT l.num FROM (VALUES (1), (0), (2), (3), (4), (5), (6), (7)) as l(num) WHERE"
    " NOT EXISTS (SELECT 1 from networking.bmv_nic n where n.vf=l.num and n.dcc_dpu_uuid='{}');"
)

#----------nexthop------------

SYNC_NEXT_HOP_UPDATES = (
    "INSERT INTO networking.bmv_next_hop_fanout (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote, bmv_subnet_uuid, bmv_vpc_uuid, dcc_vrf_uuid, local_ip, remote_ip, is_gw, delete_pending, update_pending, dest_type) "
    "(SELECT DISTINCT bmv_subnet_fanout_l.dcc_uuid, dpu_cache_l.fc_dpu_id AS fc_dpu_id, dpu_cache_r.fc_dpu_id, bmv_subnet_fanout_l.bmv_subnet_uuid, bmv_subnet_fanout_l.bmv_vpc_uuid, bmv_subnet_fanout_l.dcc_vrf_uuid, dpu_cache_l.underlay_ip, dpu_cache_r.underlay_ip, FALSE, False, True, dpu_cache_r.origin "
    "FROM networking.dpu_cache dpu_cache_l,networking.dpu_cache dpu_cache_r,networking.bmv_subnet_fanout bmv_subnet_fanout_l, networking.bmv_nic bmv_nic_r "
    "WHERE bmv_subnet_fanout_l.dcc_uuid=bmv_nic_r.dcc_network_uuid and bmv_subnet_fanout_l.fc_dpu_id=dpu_cache_l.fc_dpu_id and bmv_nic_r.dcc_dpu_uuid=dpu_cache_r.dcc_uuid  and dpu_cache_l.fc_dpu_id<>dpu_cache_r.fc_dpu_id and dpu_cache_l.origin<>'bgp') "
    "ON CONFLICT (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote) DO UPDATE SET bmv_subnet_uuid=EXCLUDED.bmv_subnet_uuid, bmv_vpc_uuid=EXCLUDED.bmv_vpc_uuid, local_ip=EXCLUDED.local_ip, remote_ip=EXCLUDED.remote_ip, is_gw=EXCLUDED.is_gw;"
)


SYNC_NEXT_HOP_BGP_UPDATES = (
    "INSERT INTO networking.bmv_next_hop_fanout (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote, bmv_subnet_uuid, bmv_vpc_uuid, dcc_vrf_uuid, local_ip, remote_ip, is_gw, delete_pending, update_pending, dest_type) "
    "(SELECT DISTINCT bmv_subnet_fanout_l.dcc_uuid, dpu_cache_l.fc_dpu_id AS fc_dpu_id, dpu_cache_r.fc_dpu_id, bmv_subnet_fanout_l.bmv_subnet_uuid, bmv_subnet_fanout_l.bmv_vpc_uuid, bmv_subnet_fanout_l.dcc_vrf_uuid, dpu_cache_l.underlay_ip, dpu_cache_r.underlay_ip, FALSE, False, True, dpu_cache_r.origin "
    "FROM networking.dpu_cache dpu_cache_l,networking.dpu_cache dpu_cache_r,networking.bmv_subnet_fanout bmv_subnet_fanout_l, networking.bgp_route bgp_route "
    "WHERE bmv_subnet_fanout_l.vxlan_id=bgp_route.vxlan_id and bmv_subnet_fanout_l.fc_dpu_id=dpu_cache_l.fc_dpu_id and "
    "dpu_cache_l.fc_dpu_id<>dpu_cache_r.fc_dpu_id and dpu_cache_l.origin<>'bgp' and dpu_cache_r.origin='bgp' and "
    " bgp_route.vtep_ip=dpu_cache_r.underlay_ip) "
    "ON CONFLICT (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote) DO UPDATE SET bmv_subnet_uuid=EXCLUDED.bmv_subnet_uuid, bmv_vpc_uuid=EXCLUDED.bmv_vpc_uuid, local_ip=EXCLUDED.local_ip, remote_ip=EXCLUDED.remote_ip, is_gw=EXCLUDED.is_gw;"
)

GET_NEXT_HOP_PENDING = (
    "SELECT  bmv_next_hop_fanout.dcc_network_uuid as dcc_network_uuid, bmv_next_hop_fanout.fc_dpu_id_local as fc_dpu_id_local, bmv_next_hop_fanout.bmv_next_hop_uuid as bmv_next_hop_uuid, bmv_next_hop_fanout.bmv_subnet_uuid as bmv_subnet_uuid, bmv_next_hop_fanout.bmv_vpc_uuid as bmv_vpc_uuid, bmv_next_hop_fanout.local_ip as local_ip, bmv_next_hop_fanout.remote_ip as remote_ip, bmv_next_hop_fanout.is_gw as is_gw, bmv_next_hop_fanout.dcc_network_uuid as dcc_network_uuid, bmv_next_hop_fanout.dcc_vrf_uuid as dcc_vrf_uuid, dpu_cache.model as model "
    "FROM networking.bmv_next_hop_fanout bmv_next_hop_fanout, networking.dpu_cache dpu_cache "
    "WHERE bmv_next_hop_fanout.update_pending=True and bmv_next_hop_fanout.delete_pending=False and bmv_next_hop_fanout.fc_dpu_id_local=dpu_cache.fc_dpu_id and dpu_cache.online=TRUE;"
)



GET_NEXT_HOP_DELETED = (
    "SELECT  bmv_next_hop_fanout.dcc_network_uuid as dcc_network_uuid, bmv_next_hop_fanout.fc_dpu_id_local as fc_dpu_id_local, bmv_next_hop_fanout.fc_dpu_id_remote as fc_dpu_id_remote, bmv_next_hop_fanout.bmv_next_hop_uuid as bmv_next_hop_uuid, bmv_next_hop_fanout.remote_ip as remote_ip, dpu_cache.model as model "
    "FROM networking.bmv_next_hop_fanout bmv_next_hop_fanout, networking.dpu_cache dpu_cache "
    "WHERE bmv_next_hop_fanout.delete_pending=True and bmv_next_hop_fanout.fc_dpu_id_local=dpu_cache.fc_dpu_id and dpu_cache.online=TRUE;"
)


SET_NEXT_HOP_PLACED = (
    "UPDATE networking.bmv_next_hop_fanout SET bmv_next_hop_uuid='{}', update_pending=False where dcc_network_uuid='{}' and fc_dpu_id_local='{}' and bmv_next_hop_fanout.remote_ip='{}' RETURNING bmv_next_hop_uuid;"
)

SYNC_NEXT_HOP_DELETE = (
    "UPDATE networking.bmv_next_hop_fanout f SET delete_pending=TRUE WHERE  NOT EXISTS (SELECT 1 FROM networking.network net, networking.dpu_cache dpu_cache_l,networking.dpu_cache dpu_cache_r  WHERE net.uuid=f.dcc_network_uuid and dpu_cache_l.fc_dpu_id=f.fc_dpu_id_local and  dpu_cache_r.fc_dpu_id=f.fc_dpu_id_remote)"
)

SYNC_NEXT_HOP_DELETE_IDLE = (
    "DELETE FROM networking.bmv_next_hop_fanout f WHERE NOT EXISTS (SELECT 1 FROM networking.network net, networking.dpu_cache dpu_cache_l,networking.dpu_cache dpu_cache_r  WHERE net.uuid=f.dcc_network_uuid and dpu_cache_l.fc_dpu_id=f.fc_dpu_id_local and  dpu_cache_r.fc_dpu_id=f.fc_dpu_id_remote) AND f.bmv_next_hop_uuid IS NULL"
)


DELETE_NEXT_HOP = (
    "DELETE FROM networking.bmv_next_hop_fanout WHERE dcc_network_uuid='{}' and fc_dpu_id_local='{}' and fc_dpu_id_remote='{}';"
)


#----------DMAC------

SYNC_DMAC_UPDATES = (
    "INSERT INTO networking.bmv_dmac_fanout (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote, mac,  bmv_next_hop_uuid, bmv_subnet_uuid, remote_ip, vlan_id, delete_pending, update_pending, learned, dest_type) "
    "(SELECT DISTINCT bmv_next_hop_fanout.dcc_network_uuid, dpu_cache_l.fc_dpu_id, dpu_cache_r.fc_dpu_id, bmv_nic.macaddress, bmv_next_hop_fanout.bmv_next_hop_uuid, bmv_next_hop_fanout.bmv_subnet_uuid, bmv_next_hop_fanout.remote_ip,   bmv_subnet_fanout.vlan_id, False, True, False, dpu_cache_r.origin "
    "FROM networking.bmv_subnet_fanout bmv_subnet_fanout, networking.bmv_next_hop_fanout bmv_next_hop_fanout, networking.dpu_cache dpu_cache_l, networking.dpu_cache dpu_cache_r, networking.bmv_nic bmv_nic "
    "WHERE bmv_nic.dcc_dpu_uuid=dpu_cache_r.dcc_uuid and bmv_next_hop_fanout.fc_dpu_id_remote=dpu_cache_r.fc_dpu_id and bmv_next_hop_fanout.dcc_network_uuid=bmv_nic.dcc_network_uuid and bmv_next_hop_fanout.fc_dpu_id_local=dpu_cache_l.fc_dpu_id and bmv_subnet_fanout.dcc_uuid=bmv_next_hop_fanout.dcc_network_uuid and dpu_cache_l.origin<>'bgp') "
    "ON CONFLICT (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote, mac) DO UPDATE SET  bmv_next_hop_uuid=EXCLUDED.bmv_next_hop_uuid, bmv_subnet_uuid=EXCLUDED.bmv_subnet_uuid, vlan_id=EXCLUDED.vlan_id;"
)


SYNC_LEARNED_DMAC_UPDATES = (
    "INSERT INTO networking.bmv_dmac_fanout (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote, mac,  bmv_next_hop_uuid, bmv_subnet_uuid, remote_ip, vlan_id, delete_pending, update_pending, learned, dest_type) "
   "SELECT bmv_vf_dmac.dcc_network_uuid, bmv_vf_dmac.fc_dpu_id_local, bmv_vf_dmac.fc_dpu_id_remote, bmv_mac_tbl.mac, bmv_vf_dmac.bmv_next_hop_uuid,bmv_vf_dmac.bmv_subnet_uuid, bmv_vf_dmac.remote_ip, bmv_vf_dmac.vlan_id, FALSE, TRUE, TRUE, 'bmv' "
   "FROM networking.bmv_mac_tbl bmv_mac_tbl, networking.bmv_dmac_fanout bmv_vf_dmac, networking.bmv_nic bmv_nic "
   "WHERE bmv_mac_tbl.fc_dpu_id=bmv_vf_dmac.fc_dpu_id_remote and bmv_mac_tbl.dcc_nic_uuid=bmv_nic.dcc_nic_uuid and bmv_nic.dcc_network_uuid=bmv_vf_dmac.dcc_network_uuid and bmv_mac_tbl.mac<>bmv_nic.macaddress "
    "ON CONFLICT (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote, mac) DO NOTHING;"
)



GET_DMAC_PENDING = (
    "SELECT  bmv_dmac_fanout.dcc_network_uuid as dcc_network_uuid, bmv_dmac_fanout.bmv_dmac_uuid as bmv_dmac_uuid, bmv_dmac_fanout.fc_dpu_id_local as fc_dpu_id_local, bmv_dmac_fanout.mac as mac, bmv_dmac_fanout.bmv_next_hop_uuid as bmv_next_hop_uuid, bmv_dmac_fanout.bmv_subnet_uuid as bmv_subnet_uuid, bmv_dmac_fanout.remote_ip as remote_ip, bmv_dmac_fanout.vlan_id as vlan_id, dpu_cache.model as model "
    "FROM networking.bmv_dmac_fanout bmv_dmac_fanout, networking.dpu_cache dpu_cache "
    "WHERE bmv_dmac_fanout.update_pending=True and bmv_dmac_fanout.delete_pending=False and bmv_dmac_fanout.fc_dpu_id_local=dpu_cache.fc_dpu_id and dpu_cache.online=TRUE;"
)

GET_DMAC_UPDATING = (
    "SELECT  bmv_dmac_fanout.dcc_network_uuid as dcc_network_uuid, bmv_dmac_fanout.bmv_dmac_uuid as bmv_dmac_uuid, bmv_dmac_fanout.fc_dpu_id_local as fc_dpu_id_local, bmv_dmac_fanout.mac as mac, bmv_dmac_fanout.bmv_next_hop_uuid as bmv_next_hop_uuid, bmv_dmac_fanout.bmv_subnet_uuid as bmv_subnet_uuid, bmv_dmac_fanout.remote_ip as remote_ip, bmv_dmac_fanout.vlan_id as vlan_id, dpu_cache.model as model "
    "FROM networking.bmv_dmac_fanout bmv_dmac_fanout, networking.dpu_cache dpu_cache "
    "WHERE bmv_dmac_fanout.update_pending=True and bmv_dmac_fanout.delete_pending=True and bmv_dmac_fanout.fc_dpu_id_local=dpu_cache.fc_dpu_id and dpu_cache.online=TRUE;"
)

REMOVE_STALE_DMAC = (
    "DELETE FROM networking.bmv_dmac_fanout f "
    "WHERE f.delete_pending=True and  f.bmv_dmac_uuid is NULL"
)

SET_DMAC_PLACED = (
    "UPDATE networking.bmv_dmac_fanout bmv_dmac_fanout SET bmv_dmac_uuid='{}', update_pending=False "
    "WHERE dcc_network_uuid='{}' and fc_dpu_id_local='{}' and mac='{}' RETURNING bmv_dmac_uuid;"
)

UNLINK_DMAC = (
    "UPDATE networking.bmv_dmac_fanout bmv_dmac_fanout SET bmv_dmac_uuid=NULL, delete_pending=False "
    "WHERE bmv_dmac_uuid='{}' ;"
)

GET_DMAC_DELETED = (
    "SELECT  bmv_dmac_fanout.dcc_network_uuid as dcc_network_uuid, bmv_dmac_fanout.bmv_dmac_uuid as bmv_dmac_uuid, bmv_dmac_fanout.fc_dpu_id_local as fc_dpu_id_local, bmv_dmac_fanout.fc_dpu_id_remote as fc_dpu_id_remote, bmv_dmac_fanout.mac as mac, bmv_dmac_fanout.bmv_next_hop_uuid as bmv_next_hop_uuid, bmv_dmac_fanout.bmv_subnet_uuid as bmv_subnet_uuid, bmv_dmac_fanout.vlan_id as vlan_id, dpu_cache.model as model "
    "FROM networking.bmv_dmac_fanout bmv_dmac_fanout, networking.dpu_cache dpu_cache "
    "WHERE bmv_dmac_fanout.delete_pending=True and bmv_dmac_fanout.update_pending=False and bmv_dmac_fanout.fc_dpu_id_local=dpu_cache.fc_dpu_id and dpu_cache.online=TRUE;"
)


SYNC_DMAC_DELETE = (
    "UPDATE networking.bmv_dmac_fanout f SET delete_pending=TRUE WHERE NOT EXISTS "
    "(SELECT 1 FROM networking.dpu_cache dpu_cache_l,networking.dpu_cache dpu_cache_r, networking.bmv_nic nic_l, networking.bmv_nic nic_r "
    " WHERE dpu_cache_l.fc_dpu_id=f.fc_dpu_id_local and  dpu_cache_r.fc_dpu_id=f.fc_dpu_id_remote and nic_l.dcc_network_uuid=f.dcc_network_uuid and nic_r.dcc_network_uuid=f.dcc_network_uuid and f.mac=nic_r.macaddress and nic_l.dcc_dpu_uuid=dpu_cache_l.dcc_uuid) "
    " AND f.learned=False"
)

SYNC_DMAC_LEARNED_DELETE = (
    "UPDATE networking.bmv_dmac_fanout f SET delete_pending=TRUE WHERE f.learned=True and NOT EXISTS "
    "(SELECT 1 FROM networking.bmv_dmac_fanout bmv_vf_dmac "
    "WHERE f.dcc_network_uuid=bmv_vf_dmac.dcc_network_uuid and bmv_vf_dmac.learned=False and f.fc_dpu_id_local=bmv_vf_dmac.fc_dpu_id_local and bmv_vf_dmac.delete_pending=FALSE) "

)


SYNC_DMAC_DELETE_IDLE = (
    "DELETE FROM networking.bmv_dmac_fanout f WHERE NOT EXISTS (SELECT 1 FROM networking.network net, networking.dpu_cache dpu_cache_l,networking.dpu_cache dpu_cache_r  WHERE net.uuid=f.dcc_network_uuid and dpu_cache_l.fc_dpu_id=f.fc_dpu_id_local and  dpu_cache_r.fc_dpu_id=f.fc_dpu_id_remote) AND f.bmv_dmac_uuid IS NULL;"
)

SYNC_DMAC_NOP = (
    "UPDATE networking.bmv_dmac_fanout SET update_pending=FALSE, delete_pending=FASLE "
    "WHERE update_pending=TRUE and delete_pending=TRUE and bmv_dmac_uuid IS NOT NULL;"
)


DELETE_DMAC = (
    "DELETE FROM networking.bmv_dmac_fanout WHERE dcc_network_uuid='{}' and fc_dpu_id_local='{}' and fc_dpu_id_remote='{}' and mac='{}';"
)


#----------- dpu cache --------------

INSERT_DPU = (
    "INSERT INTO networking.dpu_cache (dcc_uuid, fc_dpu_id, underlay_ip, server_uuid, model, online) VALUES ('{}','{}','{}','{}', '{}', '{}') "
    "ON CONFLICT (dcc_uuid) DO UPDATE SET  fc_dpu_id=EXCLUDED.fc_dpu_id, underlay_ip=EXCLUDED.underlay_ip, server_uuid=EXCLUDED.server_uuid, model=EXCLUDED.model, online=EXCLUDED.online;"
)

GET_DPU = (
    "SELECT dcc_uuid, fc_dpu_id, underlay_ip, server_uuid, model, online  FROM networking.dpu_cache where dcc_uuid='{}' "
)

GET_ALL_DPU_UUIDS = (
    "SELECT dcc_uuid FROM networking.dpu_cache WHERE model<>'gw' AND origin='bmv' "
)

GET_DPU_BY_MAC = (
    "SELECT dcc_uuid, fc_dpu_id, underlay_ip, server_uuid, model, online  FROM networking.dpu_cache where fc_dpu_id='{}' "
)

GET_ALL_GW_MACS = (
    "SELECT fc_dpu_id as mac FROM networking.dpu_cache where model='gw';"
)

GET_DPU_BY_SERVER = (
    "SELECT dcc_uuid, fc_dpu_id, underlay_ip, server_uuid, model, online  FROM networking.dpu_cache where server_uuid='{}' "
)

DELETE_DPU = (
    "DELETE FROM networking.dpu_cache WHERE  dcc_uuid='{}';"
)

DELETE_DPU_BY_MAC = (
    "DELETE FROM networking.dpu_cache WHERE  fc_dpu_id='{}';"
)

SET_DPU_ONLINE = (
    "UPDATE networking.dpu_cache SET online={} WHERE fc_dpu_id='{}'"
)

SET_ALL_DPU_ONLINE = (
    "UPDATE networking.dpu_cache SET online={}"
)

GET_COUNT_DPU_OFFLINE = (
    "SELECT COUNT(dcc_uuid) as num_offline FROM networking.dpu_cache dpu_cache "
    "WHERE dpu_cache.online=FALSE;"
)

GET_DPUS_WITH_BMV = (
    "SELECT fc_dpu_id from networking.dpu_cache dpus "
    "WHERE EXISTS (SELECT 1 FROM networking.bmv_nic nics WHERE nics.dcc_dpu_uuid=dpus.dcc_uuid and dpus.model <> 'gw');"
)

GET_DPU_IPS_WITH_BMV = (
    "SELECT underlay_ip from networking.dpu_cache dpus "
    "WHERE EXISTS (SELECT 1 FROM networking.bmv_nic nics WHERE nics.dcc_dpu_uuid=dpus.dcc_uuid and dpus.model <> 'gw');"
)


GET_DPU_IPS = (
    "SELECT underlay_ip from networking.dpu_cache dpus "
    "WHERE dpus.model <> 'gw';"
)

BGP_TO_DPU_SYNC = (
    "INSERT INTO networking.dpu_cache (dcc_uuid, fc_dpu_id, underlay_ip, server_uuid, model, online, origin) "
    "(SELECT DISTINCT ON(bgp_route.vtep_ip) gen_random_uuid(), host(bgp_route.vtep_ip), bgp_route.vtep_ip, NULL, 'bgp', TRUE, 'bgp' "
    " FROM networking.vrf_export, networking.bgp_route, networking.vrf "
    " WHERE vrf_export.route_target=bgp_route.route_target AND vrf.uuid=vrf_export.vrf_uuid AND NOT EXISTS (SELECT 1 FROM networking.dpu_cache dpu_cache2 WHERE dpu_cache2.underlay_ip=bgp_route.vtep_ip))"
)

BGP_TO_DPU_DELETE = (
    "DELETE FROM networking.dpu_cache WHERE dpu_cache.origin='bgp' AND  NOT EXISTS "
    "(SELECT 1 FROM networking.vrf_export, networking.bgp_route, networking.vrf "
    "WHERE vrf_export.route_target=bgp_route.route_target AND vrf.uuid=vrf_export.vrf_uuid AND bgp_route.vtep_ip=dpu_cache.underlay_ip)"
)




#------------ mac table ------------------
PREPARE_MAC_TBL_UPDATE = (
    "UPDATE networking.bmv_mac_tbl SET refresh_pending=TRUE "
    "WHERE fc_dpu_id='{}';"
)

PERFORM_MAC_TBL_UPDATE = (
    "INSERT INTO networking.bmv_mac_tbl(dcc_nic_uuid, mac, fc_dpu_id, refresh_pending, migrated, sequence_number) VALUES {} "
    "ON CONFLICT (dcc_nic_uuid, mac) DO UPDATE SET last_update_time=NOW(), refresh_pending=FALSE, migrated=FALSE, sequence_number=EXCLUDED.sequence_number;"
)

COMPLETE_MAC_TBL_UPDATE_MIGRATED = (
    "UPDATE networking.bmv_mac_tbl AS tbl1 SET migrated=TRUE "
    "WHERE EXISTS (select 1 FROM networking.bmv_mac_tbl AS tbl2 WHERE tbl1.migrated=FALSE "
    "AND  tbl2.fc_dpu_id <> tbl1.fc_dpu_id "
    "AND tbl2.mac=tbl1.mac AND tbl2.refresh_pending=FALSE AND tbl1.first_update_time < tbl2.first_update_time) ; "
)

COMPLETE_MAC_TBL_UPDATE_DELETED = (
    "DELETE FROM networking.bmv_mac_tbl mac_tbl WHERE ((mac_tbl.refresh_pending=TRUE and (mac_tbl.last_update_time < NOW() - INTERVAL '{}')) or mac_tbl.migrated=TRUE or NOT EXISTS (select 1 FROM networking.bmv_nic nics WHERE nics.dcc_nic_uuid=mac_tbl.dcc_nic_uuid)) ;"
)

GET_MAC_TBL_FORCED_EXPIRING = (
    "SELECT  bmv_mac_tbl.dcc_nic_uuid as dcc_nic_uuid, bmv_mac_tbl.mac as mac, "
    "bmv_mac_tbl.fc_dpu_id as fc_dpu_id, bmv_mac_tbl.sequence_number as sequence_number "
    "FROM networking.bmv_mac_tbl bmv_mac_tbl, networking.dpu_cache dpu_cache "
    "WHERE bmv_mac_tbl.migrated=True and dpu_cache.fc_dpu_id=bmv_mac_tbl.fc_dpu_id and dpu_cache.online=True;"
)

PEND_MAC_TBL_ENTRY = (
    "UPDATE networking.bmv_mac_tbl mac_tbl SET refresh_pending=TRUE WHERE mac_tbl.dcc_nic_uuid='{}' and mac_tbl.fc_dpu_id='{}' and mac_tbl.mac='{}';"
)

#---------------- bgp section ------------------

#import from BGP
SYNC_BGP_BMV_DMAC_UPDATES = (
    "INSERT INTO networking.bmv_dmac_fanout (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote, mac,  bmv_next_hop_uuid, bmv_subnet_uuid, remote_ip, vlan_id, delete_pending, update_pending, dest_type, learned) "
    "(SELECT DISTINCT bmv_next_hop_fanout.dcc_network_uuid, dpu_cache_l.fc_dpu_id, dpu_cache_r.fc_dpu_id, bgp.macaddress, bmv_next_hop_fanout.bmv_next_hop_uuid, bmv_next_hop_fanout.bmv_subnet_uuid, bmv_next_hop_fanout.remote_ip, bmv_subnet_fanout.vlan_id, False, True, dpu_cache_r.origin, TRUE "
    "FROM networking.bmv_subnet_fanout bmv_subnet_fanout, networking.bmv_next_hop_fanout bmv_next_hop_fanout, networking.dpu_cache dpu_cache_l, networking.dpu_cache dpu_cache_r, networking.bgp_route bgp "
    "WHERE bmv_next_hop_fanout.fc_dpu_id_remote=dpu_cache_r.fc_dpu_id and bmv_next_hop_fanout.remote_ip=bgp.vtep_ip and "
    "bmv_next_hop_fanout.fc_dpu_id_local=dpu_cache_l.fc_dpu_id and bmv_subnet_fanout.dcc_uuid=bmv_next_hop_fanout.dcc_network_uuid and "
    "bmv_subnet_fanout.vxlan_id=bgp.vxlan_id and  dpu_cache_l.origin<>'bgp' and dpu_cache_r.origin='bgp' and bgp.origin='bgp' and bgp.macaddress<>'00:00:00:00:00:00') "
    "ON CONFLICT (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote, mac) DO UPDATE SET  bmv_next_hop_uuid=EXCLUDED.bmv_next_hop_uuid, bmv_subnet_uuid=EXCLUDED.bmv_subnet_uuid, vlan_id=EXCLUDED.vlan_id;"
)

SYNC_BGP_BMV_DMAC_DELETE = (
    "UPDATE networking.bmv_dmac_fanout f SET delete_pending=TRUE "
    " WHERE NOT EXISTS (SELECT 1 FROM networking.network net, networking.dpu_cache dpu_cache_l,networking.dpu_cache dpu_cache_r, networking.bgp_route bgp "
    "  WHERE net.uuid=f.dcc_network_uuid and dpu_cache_l.fc_dpu_id=f.fc_dpu_id_local and  dpu_cache_r.fc_dpu_id=f.fc_dpu_id_remote and f.mac=bgp.macaddress) "
    "AND f.learned=True AND f.dest_type='bgp'"

)

#export to BGP

SYNC_BMV_BGP_UPDATES_FROM_NIC = (
    "INSERT INTO networking.bgp_route (route_distinguisher, route_target, vxlan_id, macaddress, host_ip, vtep_ip, origin, update_pending, delete_pending)"
    "(SELECT DISTINCT vrf_export.route_distinguisher, vrf_export.route_target, bmv_subnet_fanout.vxlan_id, bmv_nic.macaddress, CAST(NULL AS INET) , dpu_cache.underlay_ip, CAST('bmv' AS origin_type), TRUE, FALSE "
    "FROM networking.vrf_export vrf_export, networking.bmv_subnet_fanout bmv_subnet_fanout, networking.dpu_cache dpu_cache, networking.bmv_nic bmv_nic "
    "WHERE bmv_nic.dcc_dpu_uuid=dpu_cache.dcc_uuid and bmv_subnet_fanout.fc_dpu_id=dpu_cache.fc_dpu_id and bmv_nic.bmv_subnet_uuid=bmv_subnet_fanout.bmv_subnet_uuid and  bmv_subnet_fanout.dcc_vrf_uuid=vrf_export.vrf_uuid) "
    "ON CONFLICT ( macaddress, vxlan_id) DO UPDATE SET host_ip=EXCLUDED.host_ip, vtep_ip=EXCLUDED.vtep_ip, route_target=EXCLUDED.route_target"
)


SYNC_BMV_BGP_UPDATES_LEARNED = (
    "INSERT INTO networking.bgp_route (route_distinguisher, route_target, vxlan_id, macaddress, host_ip, vtep_ip, origin, update_pending, delete_pending)"
    "(SELECT DISTINCT vrf_export.route_distinguisher, vrf_export.route_target, bmv_subnet_fanout.vxlan_id, bmv_mac_tbl.mac, CAST(NULL AS INET) , dpu_cache.underlay_ip, CAST('learn' AS origin_type), TRUE, FALSE "
    "FROM networking.vrf_export vrf_export, networking.bmv_subnet_fanout bmv_subnet_fanout, networking.bmv_mac_tbl bmv_mac_tbl, networking.dpu_cache dpu_cache, networking.bmv_nic bmv_nic "
    "WHERE bmv_mac_tbl.fc_dpu_id=dpu_cache.fc_dpu_id and bmv_subnet_fanout.fc_dpu_id=dpu_cache.fc_dpu_id and bmv_nic.bmv_subnet_uuid=bmv_subnet_fanout.bmv_subnet_uuid and bmv_mac_tbl.dcc_nic_uuid=bmv_nic.dcc_nic_uuid and bmv_subnet_fanout.dcc_vrf_uuid=vrf_export.vrf_uuid) "
    "ON CONFLICT ( macaddress, vxlan_id) DO UPDATE SET host_ip=EXCLUDED.host_ip, vtep_ip=EXCLUDED.vtep_ip, route_target=EXCLUDED.route_target"
)

SYNC_BMV_BGP_DELETE_FROM_NIC = (
    "UPDATE networking.bgp_route bgp_route SET delete_pending=TRUE  WHERE bgp_route.origin='bmv' AND bgp_route.delete_pending=FALSE AND "
    "NOT EXISTS (SELECT 1 FROM networking.vrf_export vrf_export, networking.bmv_subnet_fanout bmv_subnet_fanout, networking.dpu_cache dpu_cache, networking.bmv_nic bmv_nic "
    "WHERE  bgp_route.macaddress=bmv_nic.macaddress and bgp_route.vxlan_id=bmv_subnet_fanout.vxlan_id and bgp_route.route_target=vrf_export.route_target "
    "    and  bmv_subnet_fanout.fc_dpu_id=dpu_cache.fc_dpu_id "
    "    and bmv_nic.bmv_subnet_uuid=bmv_subnet_fanout.bmv_subnet_uuid and dpu_cache.dcc_uuid=bmv_nic.dcc_dpu_uuid "
    "    and bmv_subnet_fanout.dcc_vrf_uuid=vrf_export.vrf_uuid) "
)

SYNC_BMV_BGP_DELETE_FROM_LEARNED = (
    "UPDATE networking.bgp_route bgp_route SET delete_pending=TRUE WHERE bgp_route.origin='learn' AND bgp_route.delete_pending=FALSE AND "
    "NOT EXISTS (SELECT 1 FROM networking.vrf_export vrf_export, networking.bmv_subnet_fanout bmv_subnet_fanout, networking.bmv_mac_tbl bmv_mac_tbl, networking.dpu_cache dpu_cache, networking.bmv_nic bmv_nic "
    "WHERE bgp_route.macaddress=bmv_mac_tbl.mac and bgp_route.vxlan_id=bmv_subnet_fanout.vxlan_id and bgp_route.route_target=vrf_export.route_target "
    "    and bmv_mac_tbl.fc_dpu_id=dpu_cache.fc_dpu_id and bmv_subnet_fanout.fc_dpu_id=dpu_cache.fc_dpu_id "
    "    and bmv_nic.bmv_subnet_uuid=bmv_subnet_fanout.bmv_subnet_uuid and bmv_mac_tbl.dcc_nic_uuid=bmv_nic.dcc_nic_uuid "
    "    and bmv_subnet_fanout.dcc_vrf_uuid=vrf_export.vrf_uuid )"
)


BMV_BGP_IS_UPDATE_NEED = (
    "SELECT COUNT(*) as total from networking.bgp_route bgp_route WHERE bgp_route.origin <> 'bgp' AND (bgp_route.update_pending=TRUE or bgp_route.delete_pending=TRUE)"
)

BMV_BGP_UPDATE_DONE = (
    "UPDATE networking.bgp_route SET update_pending=FALSE WHERE macaddress='{}' and vxlan_id={}"
)

BMV_BGP_DELETE_DONE = (
    "DELETE FROM networking.bgp_route WHERE macaddress='{}' and vxlan_id={}"
)


GET_BGP_ROUTE_PENDING = (
    "SELECT bgp_route.route_target as route_target, vrf.vrf_id as vrf_name, bgp_route.vxlan_id as vxlan_id, "
    "bgp_route.macaddress as macaddress, bgp_route.host_ip as host_ip, bgp_route.vtep_ip as vtep_ip "
    "FROM networking.bgp_route bgp_route, networking.vrf vrf, networking.vrf_export vrf_export "
    "WHERE bgp_route.update_pending=TRUE and bgp_route.delete_pending=FALSE and "
    " (bgp_route.origin='bmv' or bgp_route.origin='learn') and vrf_export.route_target=bgp_route.route_target "
    " and vrf.uuid=vrf_export.vrf_uuid;"
)

SET_ALL_PENDING = (
    "UPDATE networking.bgp_route SET update_pending=TRUE WHERE delete_pending=FALSE and "
    " (bgp_route.origin='bmv' or bgp_route.origin='learn')"
)

GET_BGP_ROUTE_DELETED = (
    "SELECT bgp_route.route_target as route_target, vrf.vrf_id as vrf_name, bgp_route.vxlan_id as vxlan_id, "
    "bgp_route.macaddress as macaddress, bgp_route.host_ip as host_ip, bgp_route.vtep_ip as vtep_ip "
    "FROM networking.bgp_route bgp_route, networking.vrf vrf, networking.vrf_export vrf_export "
    "WHERE delete_pending=TRUE and vrf_export.route_target=bgp_route.route_target and vrf.uuid=vrf_export.vrf_uuid;"
)

ADD_BGP_ROUTE = (
    "INSERT INTO networking.bgp_route (route_distinguisher, route_target, vxlan_id, macaddress, host_ip, vtep_ip, origin, update_pending, delete_pending) "
    "(SELECT NULL, vrf_export.route_target, {vxlan_id}, '{mac}', '{ip}', '{next_hop_ip}', 'bgp', FALSE, FALSE "
    "FROM networking.vrf_export vrf_export, networking.vrf vrf "
    "WHERE vrf.vrf_id='{virt_network}' and vrf_export.vrf_uuid=vrf.uuid) "
    "ON CONFLICT (macaddress, vxlan_id) DO UPDATE SET route_target=EXCLUDED.route_target, host_ip=EXCLUDED.host_ip, vtep_ip=EXCLUDED.vtep_ip"
)

IS_BGP_ROUTE_LOCAL = (
    "SELECT COUNT(*) AS v FROM networking.bgp_route bgp_route WHERE bgp_route.macaddress='{mac}' and bgp_route.vtep_ip='{next_hop_ip}' and "
    " bgp_route.origin='learn'"
)


DELETE_BGP_ROUTE = (
    "DELETE FROM networking.bgp_route bgp_route USING networking.vrf_export vrf_export, networking.vrf vrf "
    "WHERE bgp_route.route_target=vrf_export.route_target and bgp_route.macaddress='{mac}' and bgp_route.host_ip='{ip}' and vrf_export.vrf_uuid=vrf.uuid and vrf.vrf_id='{virt_network}' "
)

GET_EVPN_VRFS = (
    "SELECT vrf.vrf_id as vrf_id, vrf_export.route_target as route_target FROM networking.vrf vrf, networking.vrf_export vrf_export WHERE vrf_export.vrf_uuid=vrf.uuid;"
)
