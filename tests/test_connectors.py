from connectors.remoteok import RemoteOKConnector
from connectors.weworkremotely import WeWorkRemotelyConnector


def test_connector_interfaces():
    assert RemoteOKConnector.source == "remoteok"
    assert WeWorkRemotelyConnector.source == "weworkremotely"
