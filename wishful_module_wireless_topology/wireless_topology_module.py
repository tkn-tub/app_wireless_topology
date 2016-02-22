import logging
import wishful_controller
import wishful_upis as upis
from wishful_framework.classes import exceptions

__author__ = "Piotr Gawlowicz, Anatolij Zubow"
__copyright__ = "Copyright (c) 2015, Technische Universitat Berlin"
__version__ = "0.1.0"
__email__ = "{gawlowicz, zubow}@tkn.tu-berlin.de"


@wishful_controller.build_module
class WirelessTopologyModule(wishful_controller.ControllerUpiModule):
    def __init__(self, controller):
        super(WirelessTopologyModule, self).__init__(controller)
        self.log = logging.getLogger('wireless_topology_module.main')

