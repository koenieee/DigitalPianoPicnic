"""
Main bridge application: MIDI -> Home Assistant

Responsibilities:
- Load configuration from YAML files
- Initialize MIDI input and HA client
- Implement arming state machine (sequence/chord password)
- Track double-tap confirmation per note
- Enforce debounce and rate limiting
- Map notes to products and build service payloads
- Coordinate MIDI events -> HA service calls -> announcements
- Main event loop with graceful shutdown
"""

import os
import sys
import time
import asyncio
import logging
import signal
from typing import Dict, Optional, Set, List, Any
from dataclasses import dataclass
from enum import Enum

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML required. Install with: pip install PyYAML")

from midi import MidiInput, MidiEvent
from ha_client import HAClient, ServiceCallResult

logger = logging.getLogger(__name__)


class ArmingState(Enum):
    """Arming state for the system."""
    DISARMED = "disarmed"
    ARMED = "armed"


@dataclass
class ProductMapping:
    """Product mapping configuration."""
    product_id: str
    product_name: str
    amount: int = 1
    config_entry_id: Optional[str] = None
    confirmation: str = "double_tap"  # double_tap or single_tap


class ArmingStateMachine:
    """Manages arming/disarming state with sequence and/or chord detection."""
    
    def __init__(self, config: Dict[str, Any], ha_client: Optional['HAClient'] = None):
        self.enabled = config.get('enabled', True)
        self.sequence = config.get('sequence', [])
        self.sequence_timeout_ms = config.get('sequence_timeout_ms', 3000)
        self.chord = set(config.get('chord', []))
        self.chord_window_ms = config.get('chord_window_ms', 200)
        self.require_both = config.get('require_both_sequence_and_chord', False)
        self.disarm_after_ms = config.get('disarm_after_ms', 60000)
        self.disarm_after_add = config.get('disarm_after_add', False)
        
        # Announcement config
        self.announce_on_arm = config.get('announce_on_arm', True)
        self.announce_on_disarm = config.get('announce_on_disarm', True)
        self.arm_message = config.get('arm_message', 'Piano is now armed and ready for shopping')
        self.disarm_message = config.get('disarm_message', 'Piano has been disarmed')
        self.ha_client = ha_client
        
        self.state = ArmingState.DISARMED
        self.last_activity = time.time()
        self.sequence_progress: List[int] = []
        self.sequence_start_time = 0.0
        
        self.armed_by_sequence = False
        self.armed_by_chord = False
    
    def set_ha_client(self, ha_client: 'HAClient'):
        """Set HA client for announcements."""
        self.ha_client = ha_client
    
    async def _announce(self, message: str):
        """Send announcement via HA satellite."""
        if self.ha_client:
            try:
                result = await self.ha_client.announce(message, device_id=None, preannounce=False)
                if result.success:
                    logger.info(f"Arming announcement sent: {message}")
                else:
                    logger.warning(f"Arming announcement failed: {result.error_message}")
            except Exception as e:
                logger.error(f"Error sending arming announcement: {e}")
    
    def reset(self):
        """Reset to disarmed state."""
        previous_state = self.state
        self.state = ArmingState.DISARMED
        self.sequence_progress = []
        self.armed_by_sequence = False
        self.armed_by_chord = False
        logger.info("System DISARMED")
        
        # Announce disarm if transitioning from armed to disarmed
        if previous_state == ArmingState.ARMED and self.announce_on_disarm:
            asyncio.create_task(self._announce(self.disarm_message))
    
    def on_note(self, note: int, timestamp: float) -> ArmingState:
        """
        Process a note for arming state.
        
        Args:
            note: MIDI note number
            timestamp: Event timestamp
            
        Returns:
            Current arming state
        """
        if not self.enabled:
            return ArmingState.ARMED  # Always armed if disabled
        
        self.last_activity = timestamp
        
        # Check auto-disarm timeout
        if self.state == ArmingState.ARMED:
            if self.disarm_after_ms > 0:
                inactive_ms = (timestamp - self.last_activity) * 1000
                if inactive_ms > self.disarm_after_ms:
                    logger.info(f"Auto-disarm after {inactive_ms:.0f}ms inactivity")
                    self.reset()
        
        # If already armed, stay armed
        if self.state == ArmingState.ARMED:
            return self.state
        
        # Check sequence matching
        if self.sequence:
            self._process_sequence(note, timestamp)
        
        # Check if we should arm
        needs_sequence = bool(self.sequence)
        needs_chord = bool(self.chord)
        
        if self.require_both:
            # Need both sequence and chord
            if self.armed_by_sequence and self.armed_by_chord:
                previous_state = self.state
                self.state = ArmingState.ARMED
                logger.info("System ARMED (sequence + chord)")
                if previous_state != ArmingState.ARMED and self.announce_on_arm:
                    asyncio.create_task(self._announce(self.arm_message))
        else:
            # Need either sequence or chord
            if (needs_sequence and self.armed_by_sequence) or \
               (needs_chord and self.armed_by_chord):
                previous_state = self.state
                self.state = ArmingState.ARMED
                trigger = "sequence" if self.armed_by_sequence else "chord"
                logger.info(f"System ARMED ({trigger})")
                if previous_state != ArmingState.ARMED and self.announce_on_arm:
                    asyncio.create_task(self._announce(self.arm_message))
        
        return self.state
    
    def on_chord(self, chord_notes: Set[int], timestamp: float) -> ArmingState:
        """
        Process a detected chord for arming.
        
        Args:
            chord_notes: Set of MIDI notes in the chord
            timestamp: Event timestamp
            
        Returns:
            Current arming state
        """
        if not self.enabled or not self.chord:
            return self.state
        
        self.last_activity = timestamp
        
        # Check if chord matches
        if chord_notes == self.chord:
            self.armed_by_chord = True
            logger.info(f"Arming chord detected: {sorted(chord_notes)}")
            
            # Check if we should arm now
            if not self.require_both or self.armed_by_sequence:
                previous_state = self.state
                self.state = ArmingState.ARMED
                trigger = "chord" if not self.require_both else "sequence + chord"
                logger.info(f"System ARMED ({trigger})")
                if previous_state != ArmingState.ARMED and self.announce_on_arm:
                    asyncio.create_task(self._announce(self.arm_message))
        
        return self.state
    
    def _process_sequence(self, note: int, timestamp: float):
        """Process a note for sequence matching."""
        timeout_sec = self.sequence_timeout_ms / 1000.0
        
        # Start new sequence if empty
        if not self.sequence_progress:
            self.sequence_progress = [note]
            self.sequence_start_time = timestamp
            logger.debug(f"Sequence started: {self.sequence_progress}")
            return
        
        # Check timeout
        if timestamp - self.sequence_start_time > timeout_sec:
            logger.debug("Sequence timeout, restarting")
            self.sequence_progress = [note]
            self.sequence_start_time = timestamp
            return
        
        # Check if note continues the sequence
        expected_idx = len(self.sequence_progress)
        if expected_idx < len(self.sequence) and note == self.sequence[expected_idx]:
            self.sequence_progress.append(note)
            logger.debug(f"Sequence progress: {self.sequence_progress}")
            
            # Check if sequence complete
            if self.sequence_progress == self.sequence:
                self.armed_by_sequence = True
                logger.info(f"Arming sequence completed: {self.sequence_progress}")
        else:
            # Wrong note, restart
            logger.debug(f"Sequence broken, restarting (expected {self.sequence[expected_idx]}, got {note})")
            self.sequence_progress = [note]
            self.sequence_start_time = timestamp
    
    def on_product_added(self):
        """Called after a product is successfully added."""
        if self.disarm_after_add:
            logger.info("Disarming after product add")
            self.reset()


class RateLimiter:
    """Per-note rate limiting."""
    
    def __init__(self, rate_limit_ms: int):
        self.rate_limit_ms = rate_limit_ms
        self.last_trigger: Dict[int, float] = {}
    
    def can_trigger(self, note: int, timestamp: float) -> bool:
        """
        Check if a note can trigger an action.
        
        Args:
            note: MIDI note number
            timestamp: Current timestamp
            
        Returns:
            True if allowed, False if rate limited
        """
        if note in self.last_trigger:
            elapsed_ms = (timestamp - self.last_trigger[note]) * 1000
            if elapsed_ms < self.rate_limit_ms:
                logger.debug(f"Rate limited: note={note} elapsed={elapsed_ms:.0f}ms")
                return False
        
        self.last_trigger[note] = timestamp
        return True


class Bridge:
    """Main bridge application."""
    
    def __init__(self, config_path: str = "config/app.yaml", test_mode: bool = False):
        self.config_path = config_path
        self.config = None
        self.mapping = None
        self.test_mode = test_mode
        
        self.midi: Optional[MidiInput] = None
        self.ha_client: Optional[HAClient] = None
        
        self.arming_sm: Optional[ArmingStateMachine] = None
        self.rate_limiter: Optional[RateLimiter] = None
        
        self.running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.midi_reconnect_delay = 5  # default, overridden from config
    
    def load_config(self):
        """Load configuration from YAML files."""
        logger.info(f"Loading configuration from {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Load mapping file
        mapping_path = self.config.get('mapping_file', 'config/mapping.yaml')
        logger.info(f"Loading mapping from {mapping_path}")
        
        with open(mapping_path, 'r') as f:
            self.mapping = yaml.safe_load(f)
        
        logger.info("Configuration loaded successfully")
    
    def setup_logging(self):
        """Configure logging based on config."""
        log_config = self.config.get('logging', {})
        level = getattr(logging, log_config.get('level', 'INFO'))
        mode = log_config.get('mode', 'stdout')
        
        log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        
        if mode == 'stdout':
            logging.basicConfig(level=level, format=log_format)
        else:
            logging.basicConfig(level=level, format=log_format, filename=mode)
        
        logger.info(f"Logging configured: level={log_config.get('level')} mode={mode}")
    
    def initialize(self):
        """Initialize components."""
        # Setup logging first
        self.setup_logging()
        
        # Initialize MIDI
        midi_config = self.config.get('midi', {})
        self.midi = MidiInput(
            port_name=midi_config.get('port_name', ''),
            channel=midi_config.get('channel', 1)
        )
        
        # Set debounce and double-tap windows
        debounce_ms = midi_config.get('debounce_ms', 200)
        self.midi.chord_detector.window_ms = self.config.get('arming', {}).get('chord_window_ms', 200)
        
        confirmation_config = self.config.get('confirmation', {})
        double_tap_window = confirmation_config.get('double_tap_window_ms', 800)
        self.midi.double_tap_tracker.window_ms = double_tap_window
        
        # Initialize arming state machine
        arming_config = self.config.get('arming', {})
        self.arming_sm = ArmingStateMachine(arming_config)
        
        # Initialize rate limiter
        rate_limit_ms = midi_config.get('rate_limit_per_note_ms', 500)
        self.rate_limiter = RateLimiter(rate_limit_ms)
        
        # Runtime settings
        runtime_config = self.config.get('runtime', {})
        self.midi_reconnect_delay = runtime_config.get('midi_reconnect_delay_sec', 5)
        
        logger.info("Components initialized")
    
    def get_product_mapping(self, note: int) -> Optional[ProductMapping]:
        """Get product mapping for a note."""
        note_mappings = self.mapping.get('notes', {})
        defaults = self.mapping.get('defaults', {})
        
        # Try both integer and string keys (YAML can parse as either)
        note_data = note_mappings.get(note) or note_mappings.get(str(note))
        
        if not note_data:
            behavior = self.mapping.get('behavior', {})
            if behavior.get('out_of_range_handling') == 'log':
                logger.warning(f"No mapping for note {note} (available notes: {list(note_mappings.keys())[:10]}...)")
            return None
        
        return ProductMapping(
            product_id=note_data.get('product_id'),
            product_name=note_data.get('product_name', f"Product {note_data.get('product_id')}"),
            amount=note_data.get('amount', defaults.get('amount', 1)),
            config_entry_id=note_data.get('config_entry_id', defaults.get('config_entry_id')),
            confirmation=note_data.get('confirmation', defaults.get('confirmation', 'double_tap'))
        )
    
    async def handle_note_on(self, event: MidiEvent):
        """Handle a note_on event."""
        note = event.note
        timestamp = event.timestamp
        
        # Update arming state
        self.arming_sm.on_note(note, timestamp)
        
        # Check if armed
        if self.arming_sm.state != ArmingState.ARMED:
            logger.debug(f"Ignoring note {note}: system not armed")
            return
        
        # Get product mapping
        mapping = self.get_product_mapping(note)
        if not mapping:
            return
        
        # Check confirmation (double-tap)
        confirmation_config = self.config.get('confirmation', {})
        double_tap_enabled = confirmation_config.get('double_tap_enabled', True)
        
        if double_tap_enabled and mapping.confirmation == 'double_tap':
            is_second_tap = self.midi.check_double_tap(event)
            if not is_second_tap:
                logger.info(f"Note {note}: waiting for second tap")
                return
        
        # Check rate limiting
        if not self.rate_limiter.can_trigger(note, timestamp):
            logger.warning(f"Note {note}: rate limited")
            return
        
        # Add product
        logger.info(f"Triggering action: note={note} product={mapping.product_name} amount={mapping.amount}")
        
        if self.test_mode:
            # Test mode: fake successful calls with detailed output
            logger.info(f"[TEST MODE] Would call service: picnic.add_product")
            logger.info(f"  └─ product_id: {mapping.product_id}")
            logger.info(f"  └─ amount: {mapping.amount}")
            if mapping.config_entry_id:
                logger.info(f"  └─ config_entry_id: {mapping.config_entry_id}")
            result_success = True
            
            # Fake announcement
            announce_config = self.config.get('announce', {})
            if announce_config.get('enabled', True):
                message_template = announce_config.get('message_template', "{product_name} was added to basket")
                message = message_template.format(product_name=mapping.product_name)
                device_id = announce_config.get('device_id', 'not_set')
                preannounce = announce_config.get('preannounce', False)
                
                logger.info(f"[TEST MODE] Would call service: assist_satellite.announce")
                logger.info(f"  └─ device_id: {device_id}")
                logger.info(f"  └─ message: '{message}'")
                logger.info(f"  └─ preannounce: {preannounce}")
        else:
            # Real mode: actual HA calls
            result = await self.ha_client.add_product(
                product_id=mapping.product_id,
                amount=mapping.amount,
                config_entry_id=mapping.config_entry_id
            )
            result_success = result.success
            
            if result.success:
                logger.info(f"Product added successfully: {mapping.product_name}")
                
                # Announce if enabled
                announce_config = self.config.get('announce', {})
                if announce_config.get('enabled', True):
                    message_template = announce_config.get('message_template', "{product_name} was added to basket")
                    message = message_template.format(product_name=mapping.product_name)
                    device_id = announce_config.get('device_id')
                    preannounce = announce_config.get('preannounce', False)
                    
                    announce_result = await self.ha_client.announce(message, device_id, preannounce)
                    if not announce_result.success:
                        logger.warning(f"Announcement failed: {announce_result.error_message}")
            else:
                logger.error(f"Failed to add product: {result.error_message}")
        
        # Handle disarm-after-add
        if result_success:
            self.arming_sm.on_product_added()
    
    async def process_midi_events(self):
        """Process MIDI events in async loop with automatic reconnection."""
        logger.info("Starting MIDI event processing")
        
        loop = asyncio.get_event_loop()
        
        while self.running:
            try:
                # Open MIDI port in executor (blocking operation)
                logger.info("Attempting to connect to MIDI device...")
                await loop.run_in_executor(None, self.midi.open)
                logger.info("MIDI device connected successfully")
                
                # Process events
                for event in self.midi.read_events():
                    if not self.running:
                        logger.info("Shutdown requested, stopping MIDI processing")
                        break
                    
                    # Skip None events (polling timeouts)
                    if event is None:
                        continue
                    
                    try:
                        if event.type == 'note_on':
                            # Check for chord
                            chord = self.midi.detect_chord(event)
                            if chord:
                                self.arming_sm.on_chord(chord, event.timestamp)
                            
                            # Handle note
                            await self.handle_note_on(event)
                        
                        # Allow other async tasks to run
                        await asyncio.sleep(0)
                    
                    except KeyboardInterrupt:
                        logger.info("Keyboard interrupt in event loop")
                        self.running = False
                        break
                
                # If we exit the loop cleanly, device was closed
                logger.info("MIDI event stream ended")
                break
            
            except RuntimeError as e:
                # MIDI device disconnected or not found
                logger.warning(f"MIDI connection lost: {e}")
                logger.info("Resetting arming state due to device disconnection")
                
                # Reset arming state when device disconnects
                self.arming_sm.reset()
                
                logger.info(f"Will retry connection in {self.midi_reconnect_delay} seconds...")
                
                # Close port if it was opened
                try:
                    self.midi.close()
                except:
                    pass
                
                # Wait before retry
                await asyncio.sleep(self.midi_reconnect_delay)
            
            except Exception as e:
                logger.error(f"Unexpected MIDI error: {e}", exc_info=True)
                logger.info("Resetting arming state due to error")
                
                # Reset arming state on any error
                self.arming_sm.reset()
                
                logger.info(f"Will retry connection in {self.midi_reconnect_delay} seconds...")
                
                # Close port if it was opened
                try:
                    self.midi.close()
                except:
                    pass
                
                await asyncio.sleep(self.midi_reconnect_delay)
        
        # Final cleanup
        try:
            self.midi.close()
        except:
            pass
    
    async def run(self):
        """Main run loop."""
        self.running = True
        self.loop = asyncio.get_event_loop()
        
        if self.test_mode:
            logger.info("Bridge starting in TEST MODE (no Home Assistant connection)")
        else:
            logger.info("Bridge starting...")
        
        # Load config
        self.load_config()
        self.initialize()
        
        if not self.test_mode:
            # Get HA credentials
            ha_config = self.config.get('ha', {})
            ha_url = ha_config.get('url')
            
            token_source = ha_config.get('token_source', 'env')
            if token_source == 'env':
                ha_token = os.getenv('HA_TOKEN')
                if not ha_token:
                    logger.error("HA_TOKEN environment variable not set")
                    return
            else:
                logger.error("Only 'env' token_source is currently supported")
                return
            
            # Connect to HA
            runtime_config = self.config.get('runtime', {})
            reconnect_backoff = runtime_config.get('reconnect_backoff_ms', [500, 1000, 2000, 5000])
            
            self.ha_client = HAClient(ha_url, ha_token, reconnect_backoff)
            
            if not await self.ha_client.connect():
                logger.error("Failed to connect to Home Assistant")
                return
            
            # Set HA client for arming announcements
            if self.arming_sm:
                self.arming_sm.set_ha_client(self.ha_client)
        
        logger.info("Bridge running. Press Ctrl+C to stop.")
        
        try:
            # Process MIDI events
            await self.process_midi_events()
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        
        except Exception as e:
            logger.error(f"Bridge error: {e}", exc_info=True)
        
        finally:
            self.running = False
            if self.ha_client:
                await self.ha_client.disconnect()
            logger.info("Bridge stopped")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        # If there's an event loop, stop it
        if self.loop and self.loop.is_running():
            self.loop.stop()


def main():
    """Entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='MIDI to Home Assistant Bridge',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Normal mode (requires Home Assistant connection):
  python3 bridge.py
  
  # Test mode (no Home Assistant, fake calls):
  python3 bridge.py --test
  
  # Custom config path:
  python3 bridge.py --config /path/to/config.yaml
  
  # Test mode with custom config:
  python3 bridge.py --test --config /path/to/config.yaml
        """
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode (no Home Assistant connection, fake service calls)'
    )
    parser.add_argument(
        '--config',
        default=os.getenv('CONFIG_PATH', 'config/app.yaml'),
        help='Path to config file (default: config/app.yaml or $CONFIG_PATH)'
    )
    
    args = parser.parse_args()
    
    bridge = Bridge(args.config, test_mode=args.test)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, bridge.signal_handler)
    signal.signal(signal.SIGTERM, bridge.signal_handler)
    
    # Run
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
