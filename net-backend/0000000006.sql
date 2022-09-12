BEGIN TRANSACTION;

CREATE TABLE networking.bmv_vpc_fanout
(
    dcc_uuid uuid,
    fc_dpu_id VARCHAR(17),
    bmv_vpc_uuid uuid,
    route_target VARCHAR(32),
    delete_pending BOOLEAN NOT NULL DEFAULT FALSE,
    update_pending BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (dcc_uuid, fc_dpu_id)
);

CREATE OR REPLACE FUNCTION networking.bmv_vpc_fanout_handle()
RETURNS TRIGGER AS $$
BEGIN
  RAISE NOTICE 'TG_OP is currently %', TG_OP;
  IF (TG_OP = 'INSERT') THEN
    NEW.update_pending:=TRUE;
  ELSIF (TG_OP = 'UPDATE') THEN
    IF (NEW.route_target <> OLD.route_target) THEN
        NEW.update_pending:=TRUE;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ language 'plpgsql';


CREATE TRIGGER bmv_vpc_fanout_trigger
       BEFORE INSERT OR UPDATE ON networking.bmv_vpc_fanout
       FOR EACH ROW EXECUTE PROCEDURE networking.bmv_vpc_fanout_handle();

CREATE TABLE networking.dpu_cache
(
    dcc_uuid uuid,
    fc_dpu_id VARCHAR(17),
    overlay_ip Inet,
    server_uuid uuid,
    online BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (dcc_uuid)
);

CREATE TABLE networking.bmv_subnet_fanout
(
    dcc_uuid uuid,
    fc_dpu_id VARCHAR(17),
    bmv_subnet_uuid uuid,
    bmv_vpc_uuid uuid,
    dcc_vrf_uuid uuid,
    gateway Inet,
    vlan_id BigInt,
    vxlan_id BigInt,
    delete_pending BOOLEAN NOT NULL,
    update_pending BOOLEAN NOT NULL,
    PRIMARY KEY (dcc_uuid, fc_dpu_id)
);


CREATE OR REPLACE FUNCTION networking.bmv_subnet_fanout_handle()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    NEW.update_pending:=TRUE;
  ELSIF (TG_OP = 'UPDATE') THEN
    IF (NEW.gateway <> OLD.gateway or NEW.vlan_id <> OLD.vlan_id or NEW.vxlan_id <> OLD.vxlan_id) THEN
        NEW.update_pending:=TRUE;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER bmv_subnet_fanout_trigger
       BEFORE INSERT OR UPDATE ON networking.bmv_subnet_fanout
       FOR EACH ROW EXECUTE PROCEDURE networking.bmv_subnet_fanout_handle();


CREATE TABLE networking.bmv_nic
(
    dcc_nic_uuid uuid,
    dcc_dpu_uuid uuid,
    dcc_network_uuid uuid,
    bmv_nic_uuid uuid,
    bmv_vpc_uuid uuid,
    dcc_vrf_uuid uuid,
    bmv_subnet_uuid uuid,

    macaddress Macaddr NOT NULL,
    hu int,
    controller int,
    pf int,
    vf int,
    delete_pending BOOLEAN NOT NULL,
    update_pending BOOLEAN NOT NULL,

    PRIMARY KEY (dcc_nic_uuid)
);

CREATE OR REPLACE FUNCTION networking.bmv_nic_handle()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    NEW.update_pending:=TRUE;
  ELSIF (TG_OP = 'UPDATE') THEN
    IF (NEW.dcc_network_uuid <> OLD.dcc_network_uuid or NEW.macaddress <> OLD.macaddress) THEN
        NEW.update_pending:=TRUE;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER bmv_nic_trigger
       BEFORE INSERT OR UPDATE ON networking.bmv_nic
       FOR EACH ROW EXECUTE PROCEDURE networking.bmv_nic_handle();

CREATE TABLE networking.bmv_next_hop_fanout
(
    dcc_network_uuid uuid,
    fc_dpu_id_local VARCHAR(64),
    fc_dpu_id_remote VARCHAR(64),

    bmv_next_hop_uuid uuid,
    bmv_subnet_uuid uuid,
    bmv_vpc_uuid uuid,
    dcc_vrf_uuid uuid,
    local_ip Inet,
    remote_ip Inet,
    is_gw BOOLEAN,
    delete_pending BOOLEAN NOT NULL,
    update_pending BOOLEAN NOT NULL,
    PRIMARY KEY (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote)
);

CREATE OR REPLACE FUNCTION networking.bmv_next_hop_fanout_handle()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    NEW.update_pending:=TRUE;
  ELSIF (TG_OP = 'UPDATE') THEN
    IF (NEW.bmv_subnet_uuid <> OLD.bmv_subnet_uuid or NEW.bmv_vpc_uuid <> OLD.bmv_vpc_uuid or NEW.remote_ip <> OLD.remote_ip or NEW.local_ip <> OLD.local_ip or NEW.is_gw <> OLD.is_gw ) THEN
        NEW.update_pending:=TRUE;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER bmv_next_hop_fanout_trigger
       BEFORE INSERT OR UPDATE ON networking.bmv_next_hop_fanout
       FOR EACH ROW EXECUTE PROCEDURE networking.bmv_next_hop_fanout_handle();


CREATE TABLE networking.bmv_dmac_fanout
(
    dcc_network_uuid uuid,

    fc_dpu_id_local VARCHAR(17),
    fc_dpu_id_remote VARCHAR(17),

    mac Macaddr,

    bmv_dmac_uuid uuid,

    bmv_next_hop_uuid uuid,
    remote_ip Inet,
    bmv_subnet_uuid uuid,

    vlan_id BigInt,

    delete_pending BOOLEAN NOT NULL,
    update_pending BOOLEAN NOT NULL,
    PRIMARY KEY (dcc_network_uuid, fc_dpu_id_local, fc_dpu_id_remote,mac)
);


CREATE OR REPLACE FUNCTION networking.bmv_dmac_fanout_handle()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    NEW.update_pending:=TRUE;
  ELSIF (TG_OP = 'UPDATE') THEN
    IF (NEW.bmv_dmac_uuid <> OLD.bmv_dmac_uuid or NEW.bmv_subnet_uuid <> OLD.bmv_subnet_uuid or NEW.vlan_id <> OLD.vlan_id or NEW.bmv_next_hop_uuid <> OLD.bmv_next_hop_uuid ) THEN
        NEW.update_pending:=TRUE;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER bmv_dmac_fanout_trigger
       BEFORE INSERT OR UPDATE ON networking.bmv_dmac_fanout
       FOR EACH ROW EXECUTE PROCEDURE networking.bmv_dmac_fanout_handle();

END TRANSACTION;
