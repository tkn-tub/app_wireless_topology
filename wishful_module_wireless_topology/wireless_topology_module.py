import logging
import wishful_controller
import wishful_upis as upis
from wishful_framework.classes import exceptions
import itertools
import pickle
import time
import datetime

__author__ = "Piotr Gawlowicz, Anatolij Zubow"
__copyright__ = "Copyright (c) 2015, Technische Universitat Berlin"
__version__ = "0.1.0"
__email__ = "{gawlowicz, zubow}@tkn.tu-berlin.de"


@wishful_controller.build_module
class WirelessTopologyModule(wishful_controller.ControllerUpiModule):
    def __init__(self, controller):
        super(WirelessTopologyModule, self).__init__(controller)
        self.log = logging.getLogger('wireless_topology_module.main')

    @wishful_controller.bind_function(upis.global_upi.estimate_nodes_in_carrier_sensing_range)
    def estimate_nodes_in_carrier_sensing_range(self, nodes, iface, channel, TAU):
        """
        Test to find out whether two nodes in the network are in carrier sensing range using UPIs.
        For a network with N nodes all combinations are evaluated, i.e. N over 2.
        Note: make sure ptpd is running: sudo /etc/init.d/ptp-daemon
        @return a list of triples (node1, node2, True/False) True/False if nodes are in carrier sensing range
        """

        self.log.debug("is_in_carrier_sensing_range for nodes: %s" % str(nodes))

        if (len(nodes) < 2):
            self.log.error('For this test we need at least two nodes.')
            return None

        res = []
        nodeIds = range(0, len(nodes))
        groups = itertools.combinations(nodeIds, 2)
        for subgroup in groups:
            #print(subgroup)
            # testing scenario
            node1 = nodes[subgroup[0]]
            node2 = nodes[subgroup[1]]

            # exec experiment for each pair of nodes
            isInCs = self.is_in_carrier_sensing_range(node1, node2, iface, TAU, channel)
            res.append([node1,node2,isInCs])

        return res


    @wishful_controller.bind_function(upis.global_upi.is_in_carrier_sensing_range)
    def is_in_carrier_sensing_range(self, node1, node2, mon_dev='mon2', TAU=0.9, rfCh=52):
        """
        Helper functions to find out whether two nodes are in carrier sensing range using UPIs.
        @return True if nodes are in carrier sensing range
        """

        nodes = []
        nodes.append(node1)
        nodes.append(node2)
        if (len(nodes) < 2):
            self.log.error('For this test we need at least two nodes.')
            return None

        self.log.info('Testing carrier sensing range between %s and %s' % (str(node1), str(node2)))

        single_tx_rate_stats = {}
        parallel_tx_rate_stats = {}
        rel_rate_cmp_single = {}

        isInCs = {}

        def csResultCollector(group, nodeId, data):
            self.log.info('CS callback %d: receives data msg from %s : %s' % (group, nodeId, data))

            parallel_tx_rate_stats[peer_node] = float(data)
            rel_rate_cmp_single[peer_node] = parallel_tx_rate_stats[peer_node] / single_tx_rate_stats[peer_node]
            self.log.info('Relative rate cmp to single for %s is %.2f' % (peer_node, rel_rate_cmp_single[peer_node]))

            self.log.info('')
            if (len(rel_rate_cmp_single) == 2):
                # done
                if min(rel_rate_cmp_single.values()) <= float(TAU):
                    isInCs['res'] = True
                else:
                    isInCs['res'] = False

        try:
            # Set channel is currently disabled, it is not needed because
            # we automatically set the channel when we start the initial
            # experiment scripts for each participating node.
            #
            # self.log.debug('(1) set both nodes on the same channel.')
            # UPI_G call: exec remote function on UPI_R/N in 3 seconds
            # UPIfunc = UPI_RN.setParameterLowerLayer
            # remote function args
            # UPIargs = {'KEY' : (UPI_RN.IEEE80211_CHANNEL, mon_dev), 'VALUE' : (rfCh,)}

            # exec_time = None
            # rvalue = self._upi_g.runAt(nodes, UPIfunc, UPIargs, exec_time)
            # self.log.debug('Setting channel: %s' % str(rvalue))

            # time.sleep(1)

            self.log.debug('(2) single flow at %s' % str(node1))
            rv = self.controller.nodes(node1).blocking(True).net.gen_backlogged_80211_l2_bcast_traffic(mon_dev, 1000, 1350, 12, "1.1.1.1", "2.2.2.2", True)

            peer_node = node1
            single_tx_rate_stats[peer_node] = rv

            time.sleep(1)

            self.log.debug('(3) single flow at %s' % str(node2))
            rv = self.controller.nodes(node2).blocking(True).net.gen_backlogged_80211_l2_bcast_traffic(mon_dev, 1000, 1350, 12, "1.1.1.1", "2.2.2.2", True)

            peer_node = node2
            single_tx_rate_stats[peer_node] = rv

            self.log.info('single_tx_rate_stats = %s' % str(single_tx_rate_stats))

            time.sleep(1)

            self.log.debug('(4) two flows at same time %s' % str(nodes))
            exec_time = datetime.datetime.now() + datetime.timedelta(seconds=3)
            rv = self.controller.exec_time(exec_time).callback(csResultCollector).node(nodes).net.gen_backlogged_80211_l2_bcast_traffic(mon_dev, 1000, 1350, 12, "1.1.1.1", "2.2.2.2", True)

            while len(isInCs)==0:
                self.log.debug('waiting for results ...')
                time.sleep(1)

        except Exception as e:
            self.log.fatal("An error occurred (e.g. scheduling events in the past): %s" % e)

        return isInCs['res']

    @wishful_controller.bind_function(upis.global_upi.estimate_nodes_in_communication_range)
    def estimate_nodes_in_communication_range(self, nodes, iface, channel, MINPDR):
        """
        Test to find out whether two nodes in the network are in communication range using UPIs.
        For a network with N nodes all combinations are evaluated, i.e. N over 2.
        Note: make sure ptpd is running: sudo /etc/init.d/ptp-daemon
        @return a list of triples (node1, node2, True/False) True/False if nodes are in communication range
        """

        self.log.info('Nodes to tested for comm. range %s' % str(nodes))

        if (len(nodes) < 2):
            self.log.error('For this test we need at least two nodes.')
            return None

        res = []
        nodeIds = range(0, len(nodes))
        groups = itertools.combinations(nodeIds, 2)
        for subgroup in groups:
            #print(subgroup)
            # testing scenario
            node1 = nodes[subgroup[0]]
            node2 = nodes[subgroup[1]]

            # exec experiment for each pair of nodes
            isInComm = self.is_in_communication_range(node1, node2, iface, MINPDR, channel)
            res.append([node1,node2,isInComm])

        return res

    @wishful_controller.bind_function(upis.global_upi.is_in_communication_range)
    def is_in_communication_range(self, node1, node2, mon_dev='mon2', MINPDR=0.9, rfCh=52):

        """
        Helper functions to find out whether two nodes are in communication range using UPIs.
        @return True if nodes are in communication range
        """

        nodes = []
        nodes.append(node1)
        nodes.append(node2)
        if (len(nodes) < 2):
            self.log.error('For this test we need at least two nodes.')
            return None

        self.log.info('Testing communication range between %s and %s' % (str(node1), str(node2)))

        rxPkts = {}

        def csResultCollector(json_message, funcId):
            time_val = json_message['time']
            peer_node = json_message['peer']
            messagedata = json_message['msg']
            self.log.info('CommRange callback %d: receives data msg at %s from %s : %s' % (funcId, str(time_val), peer_node, messagedata))

            if messagedata is None:
                rxPkts['res'] = 0
            else:
                rxPkts['res'] = int(messagedata)

        try:
            # Set channel is currently disabled, it is not needed because
            # we automatically set the channel when we start the initial
            # experiment scripts for each participating node.
            #
            # self.log.debug('(1) set both nodes on the same channel.')
            # UPI_G call: exec remote function on UPI_R/N in 3 seconds
            # UPIfunc = UPI_RN.setParameterLowerLayer
            # remote function args
            # UPIargs = ...

            # exec_time = None
            # rvalue = self._upi_g.runAt(nodes, UPIfunc, UPIargs, exec_time)
            # self.log.debug('Setting channel: %s' % str(rvalue))

            # time.sleep(1)

            self.log.debug('(2) sniff traffic at %s' % str(node1))
            exec_time = datetime.datetime.now() + datetime.timedelta(seconds=2)
            rv = self.controller.exec_time(exec_time).callback(csResultCollector).node(node1).net.sniff_80211_l2_link_probing(mon_dev, "1.1.1.1", "2.2.2.2", 5)

            self.log.debug('(2) gen traffic at %s' % str(node2))
            exec_time = datetime.datetime.now() + datetime.timedelta(seconds=3)
            rv = self.controller.exec_time(exec_time).node(node2).net.gen_80211_l2_link_probing(mon_dev, 255, 0.01, "1.1.1.1", "2.2.2.2")

            while len(rxPkts)==0:
                self.log.debug('commrange waiting for results ...')
                time.sleep(1)

        except Exception as e:
            self.log.fatal("An error occurred (e.g. scheduling events in the past): %s" % e)

        # calc PDR
        pdr = rxPkts['res'] / float(255)

        minPdrFloat = float(MINPDR)
        self.log.info('PDR between %s and %s is %.2f (%.2f)' % (str(node1), str(node2), pdr, minPdrFloat))

        if pdr >= minPdrFloat:
            return True
        else:
            return False