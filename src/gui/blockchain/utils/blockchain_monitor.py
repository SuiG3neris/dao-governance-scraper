# src/gui/blockchain/utils/blockchain_monitor.py

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from typing import Dict, List, Set, Optional
import threading
import queue
import logging
import time
from web3 import Web3
from datetime import datetime

class NetworkStatus:
    """Container for network status information."""
    def __init__(self, chain_id: int = 0):
        self.chain_id = chain_id
        self.latest_block = 0
        self.sync_status = False
        self.peer_count = 0
        self.last_update = datetime.now()
        self.connection_healthy = False
        self.error_count = 0

class ContractStatus:
    """Container for contract status information."""
    def __init__(self, address: str):
        self.address = address
        self.last_transaction = None
        self.event_count = 0
        self.tracked_events: Set[str] = set()
        self.last_event = None
        self.error_count = 0

class BlockchainMonitor(QObject):
    """Monitors blockchain networks and contracts in real-time."""

    # Signals for UI updates
    status_updated = pyqtSignal(dict)  # General status updates
    network_error = pyqtSignal(str, str)  # Network-specific errors
    contract_event = pyqtSignal(str, dict)  # Contract events
    block_processed = pyqtSignal(str, int)  # New block processed
    alert_triggered = pyqtSignal(str, str)  # Custom alerts

    def __init__(self):
        super().__init__()
        
        # State tracking
        self.networks: Dict[str, NetworkStatus] = {}
        self.contracts: Dict[str, ContractStatus] = {}
        self.web3_instances: Dict[str, Web3] = {}
        
        # Threading components
        self.running = False
        self.event_queue = queue.Queue()
        self.monitor_thread = None
        self.lock = threading.Lock()
        
        # Update timer for UI
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._emit_status_update)
        
    def start(self):
        """Start monitoring."""
        with self.lock:
            if not self.running:
                self.running = True
                self.monitor_thread = threading.Thread(
                    target=self._monitor_loop,
                    daemon=True
                )
                self.monitor_thread.start()
                self.update_timer.start(1000)  # Update UI every second
                logging.info("Blockchain monitor started")

    def stop(self):
        """Stop monitoring."""
        with self.lock:
            self.running = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5.0)
            self.update_timer.stop()
            logging.info("Blockchain monitor stopped")

    def add_network(self, network_config: dict):
        """
        Add a network for monitoring.
        
        Args:
            network_config: Network configuration dictionary
        """
        try:
            network_id = network_config['id']
            
            # Initialize Web3 connection
            if network_config['type'].lower() == 'evm':
                provider_url = network_config['rpc_url']
                web3 = Web3(Web3.HTTPProvider(provider_url))
                
                if not web3.is_connected():
                    raise Exception("Failed to connect to network")
                    
                self.web3_instances[network_id] = web3
                
                # Initialize network status
                with self.lock:
                    self.networks[network_id] = NetworkStatus(
                        chain_id=web3.eth.chain_id
                    )
                    
            logging.info(f"Added network: {network_id}")
            
        except Exception as e:
            logging.error(f"Error adding network: {str(e)}")
            self.network_error.emit(network_id, str(e))

    def remove_network(self, network_id: str):
        """
        Remove a network from monitoring.
        
        Args:
            network_id: Network identifier
        """
        with self.lock:
            self.networks.pop(network_id, None)
            self.web3_instances.pop(network_id, None)
            
            # Remove associated contracts
            to_remove = [
                addr for addr, contract in self.contracts.items()
                if contract.network_id == network_id
            ]
            for addr in to_remove:
                self.contracts.pop(addr)
                
        logging.info(f"Removed network: {network_id}")

    def track_contract(self, contract_info: dict):
        """
        Add a contract for monitoring.
        
        Args:
            contract_info: Contract information dictionary
        """
        try:
            address = contract_info['address']
            network = contract_info['network']
            
            if network not in self.web3_instances:
                raise Exception(f"Network {network} not configured")
                
            # Initialize contract status
            with self.lock:
                contract_status = ContractStatus(address)
                contract_status.tracked_events = set(contract_info.get('events', []))
                self.contracts[address] = contract_status
                
            logging.info(f"Added contract tracking: {address}")
            
        except Exception as e:
            logging.error(f"Error adding contract: {str(e)}")
            self.network_error.emit(network, str(e))

    def untrack_contract(self, address: str):
        """
        Remove contract from monitoring.
        
        Args:
            address: Contract address
        """
        with self.lock:
            self.contracts.pop(address, None)
        logging.info(f"Removed contract tracking: {address}")

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Monitor each network
                for network_id, web3 in self.web3_instances.items():
                    self._check_network_status(network_id, web3)
                    
                # Process events
                while not self.event_queue.empty():
                    self._process_event(self.event_queue.get_nowait())
                    
            except Exception as e:
                logging.error(f"Monitor loop error: {str(e)}")
                
            time.sleep(1)  # Prevent tight loop

    def _check_network_status(self, network_id: str, web3: Web3):
        """Check status of a specific network."""
        try:
            with self.lock:
                status = self.networks[network_id]
                
                # Update basic status
                status.connection_healthy = web3.is_connected()
                status.peer_count = web3.net.peer_count
                
                # Get latest block
                new_block = web3.eth.block_number
                if new_block > status.latest_block:
                    status.latest_block = new_block
                    self.block_processed.emit(network_id, new_block)
                    
                    # Check tracked contracts
                    self._check_contracts(network_id, web3, new_block)
                    
                # Check sync status
                sync_status = web3.eth.syncing
                status.sync_status = bool(sync_status)
                
                status.last_update = datetime.now()
                
        except Exception as e:
            logging.error(f"Network status error: {str(e)}")
            with self.lock:
                status = self.networks[network_id]
                status.error_count += 1
                status.connection_healthy = False

    def _check_contracts(self, network_id: str, web3: Web3, block_number: int):
        """Check tracked contracts for new events."""
        for address, contract in self.contracts.items():
            try:
                # Get contract events
                for event_name in contract.tracked_events:
                    events = self._get_contract_events(
                        web3, address, event_name, block_number
                    )
                    for event in events:
                        self.event_queue.put({
                            'contract': address,
                            'event': event_name,
                            'data': event
                        })
                        
            except Exception as e:
                logging.error(f"Contract check error: {str(e)}")
                contract.error_count += 1

    def _get_contract_events(self, web3: Web3, address: str, 
                           event_name: str, block_number: int) -> List[dict]:
        """Get events for a specific contract."""
        # TODO: Implement event fetching logic
        return []

    def _process_event(self, event_data: dict):
        """Process a contract event."""
        try:
            self.contract_event.emit(
                event_data['contract'],
                {
                    'event': event_data['event'],
                    'data': event_data['data']
                }
            )
        except Exception as e:
            logging.error(f"Event processing error: {str(e)}")

    def _emit_status_update(self):
        """Emit current status for UI updates."""
        with self.lock:
            status = {
                'active_networks': len(self.networks),
                'tracked_contracts': len(self.contracts),
                'latest_blocks': {
                    net_id: status.latest_block
                    for net_id, status in self.networks.items()
                },
                'connection_status': {
                    net_id: status.connection_healthy
                    for net_id, status in self.networks.items()
                }
            }
            self.status_updated.emit(status)