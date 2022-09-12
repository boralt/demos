import pytest
import connexion
import os
import re

from pytest_postgresql import factories
from .resources.db_test_data import DB_TEST_DATA
from pkg_resources import resource_filename
from bmv.bmv_dao import BmvSystemDao
from service.config import Config
from service.database import PostgresClient

import socket
import threading
import socketserver


postgresql_noproc = factories.postgresql_noproc(host='localhost', user='postgres', port=5432, password='postgres')
postgresql = factories.postgresql('postgresql_noproc', db_name='networking_test')
_test_dao=None


def parse_sql_file(filename):
    ''' Return list of sql statements '''
    res = []
    embedding_started = False
    with open(filename) as f:
        lines = f.readlines()
        current_statement = ""
        for line in lines:
            if line.find('$$') >= 0:
                embedding_started = not embedding_started
            current_statement += line
            if not embedding_started and line.find(';') >= 0:
                res.append(current_statement)
                current_statement = ""
    return res


@pytest.fixture()
def pgconn(postgresql):
    cur = postgresql.cursor()
    cur.execute('DROP SCHEMA IF EXISTS networking CASCADE;')
    cur.execute('CREATE SCHEMA networking;')
    postgresql.commit()

    db_migration_script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'db_init', 'migrations')
    db_migration_files = os.listdir(db_migration_script_path)

    # Get all .sql files
    db_migration_files = [migration_file for migration_file in db_migration_files if '.sql' in migration_file]
    # sort the sql files
    db_migration_files.sort(key=lambda f: int(re.sub(r'\D', '', f)))

    for migration_file in db_migration_files:
        schema_read = parse_sql_file(f'{db_migration_script_path}/{migration_file}')
        schema_read.pop()
        for stmt in schema_read:
            cur.execute(f'{stmt};')
    postgresql.commit()
    return postgresql


@pytest.fixture(autouse=True)
def test_client(pgconn):
    global _test_dao
    pg_params = pgconn.get_dsn_parameters()
    config = Config.load('config.yaml')

    config.dao.database.host = pg_params['host']
    config.dao.database.user = 'postgres'
    config.dao.database.database_name = pg_params['dbname']
    config.dao.database.port = pg_params['port']
    config.dao.migrate = False
    config.dao.database.password = 'postgres'
    config.dao.database.connection_retry_count = 10
    config.dao.database.connection_retry_delay_seconds = 3
    postgre_client = PostgresClient(**config.dao.database)
    postgre_client.connect()
    _test_dao = BmvSystemDao(postgre_client)

@pytest.fixture()
def test_dao():
    return _test_dao

@pytest.fixture()
def populate_database(postgresql):
    cur = postgresql.cursor()
    for test_data in DB_TEST_DATA:
        cur.execute(test_data)
    postgresql.commit()


END_OF_RIB_MSG=b'''<message from="network-control@contrailsystems.com" to="agent@vnsw.contrailsystems.com/bgp-peer">
        <event xmlns="http://jabber.org/protocol/pubsub">
<items node="0/0/EndOfRib"></items>
        </event>
</message>'''





# Xmpp test helpers
class XmppRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        acc_str = ""
        started = False
        while True:
            msg = self.request.recv(1024)
            if not msg:
                break;
            msg_str = str(msg, 'ascii')
            if not started:
                acc_str += msg_str
                # scan for stream beginning according to XEP-0198
                find1 = acc_str.find('<stream:stream')
                find2 = acc_str.find('>')
                if 0 <= find1 < find2:
                    started = True
                    self.server.add_req(acc_str[find1:find2+1])
                    self.request.sendall(END_OF_RIB_MSG)
                    acc_str = acc_str[find2+1:]
            else:
                acc_str += msg_str
                while acc_str.find("</iq>") > 0:
                    end_xml_offset = acc_str.find("</iq>")
                    if end_xml_offset > 0:
                        self.server.add_req(acc_str[0:end_xml_offset+5])
                        acc_str = acc_str[end_xml_offset+5:]

#class XmppMockServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
class XmppMockServer(socketserver.ThreadingTCPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.recv_data = []
    def add_req(self, req):
        self.recv_data.append(req)

@pytest.fixture()
def xmppMockServer():
    _xmppMockServer = XmppMockServer(('127.0.0.1', 5222), XmppRequestHandler)
    with _xmppMockServer:
        server_thread = threading.Thread(target=_xmppMockServer.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        yield _xmppMockServer
