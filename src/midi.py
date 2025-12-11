"""
MIDI input handling for Digital Piano -> Home Assistant integration.

Responsibilities:
- List and open MIDI input ports
- Read MIDI events (note_on, note_off, control_change)
- Detect chords (multiple notes within time window)
- Track note state and timing for double-tap detection
- Filter by MIDI channel
"""

import time
from dataclasses import dataclass
from typing import List, Optional, Set, Dict
import logging

try:
    import mido
    from mido import Message
except ImportError:
    raise ImportError(
        "mido and python-rtmidi are required. "
        "Install with: pip install mido python-rtmidi"
    )

logger = logging.getLogger(__name__)


@dataclass
class MidiEvent:
    """Represents a MIDI event with timestamp."""
    type: str  # 'note_on', 'note_off', 'control_change'
    note: Optional[int] = None  # MIDI note number (0-127)
    velocity: Optional[int] = None  # Velocity (0-127)
    control: Optional[int] = None  # CC number
    value: Optional[int] = None  # CC value
    channel: int = 1  # MIDI channel (1-16)
    timestamp: float = 0.0  # Unix timestamp


class ChordDetector:
    """Detects when multiple notes are pressed within a time window."""
    
    def __init__(self, window_ms: int = 200):
        self.window_ms = window_ms
        self.recent_notes: Dict[int, float] = {}  # note -> timestamp
    
    def add_note(self, note: int, timestamp: float) -> Optional[Set[int]]:
        """
        Add a note press. Returns a set of notes if a chord is detected.
        
        Args:
            note: MIDI note number
            timestamp: Unix timestamp of the press
            
        Returns:
            Set of notes if chord detected, None otherwise
        """
        # Clean old notes outside the window
        window_sec = self.window_ms / 1000.0
        cutoff = timestamp - window_sec
        self.recent_notes = {n: t for n, t in self.recent_notes.items() if t >= cutoff}
        
        # Add current note
        self.recent_notes[note] = timestamp
        
        # Return chord if multiple notes in window
        if len(self.recent_notes) >= 2:
            return set(self.recent_notes.keys())
        
        return None
    
    def clear(self):
        """Clear all tracked notes."""
        self.recent_notes.clear()


class DoubleTapTracker:
    """Tracks double-tap state for each note."""
    
    def __init__(self, window_ms: int = 800):
        self.window_ms = window_ms
        self.first_taps: Dict[int, float] = {}  # note -> timestamp of first tap
    
    def on_press(self, note: int, timestamp: float) -> bool:
        """
        Register a note press. Returns True if this is the second tap.
        
        Args:
            note: MIDI note number
            timestamp: Unix timestamp of the press
            
        Returns:
            True if this completes a double-tap, False if this is the first tap
        """
        window_sec = self.window_ms / 1000.0
        
        if note in self.first_taps:
            # Check if within window
            if timestamp - self.first_taps[note] <= window_sec:
                # Second tap!
                del self.first_taps[note]
                logger.debug(f"Double-tap confirmed note={note}")
                return True
            else:
                # Outside window, reset
                self.first_taps[note] = timestamp
                logger.debug(f"Double-tap expired, reset note={note}")
                return False
        else:
            # First tap
            self.first_taps[note] = timestamp
            logger.debug(f"Double-tap first press note={note}")
            return False
    
    def clear(self, note: Optional[int] = None):
        """Clear tracking for a note, or all notes if note is None."""
        if note is None:
            self.first_taps.clear()
        elif note in self.first_taps:
            del self.first_taps[note]


class MidiInput:
    """Manages MIDI input port and event reading."""
    
    def __init__(self, port_name: str = "", channel: int = 1):
        """
        Initialize MIDI input.
        
        Args:
            port_name: Exact port name, or empty for auto-select
            channel: MIDI channel to filter (1-16), or 0 for all channels
        """
        self.port_name = port_name
        self.channel = channel
        self.port = None
        self.chord_detector = ChordDetector()
        self.double_tap_tracker = DoubleTapTracker()
    
    @staticmethod
    def list_ports() -> List[str]:
        """List all available MIDI input ports."""
        return mido.get_input_names()
    
    def open(self):
        """Open the MIDI input port."""
        available_ports = self.list_ports()
        
        if not available_ports:
            raise RuntimeError("No MIDI input ports found. Is your piano connected?")
        
        # Auto-select or find specific port
        if not self.port_name:
            selected_port = available_ports[0]
            logger.info(f"Auto-selected MIDI port: {selected_port}")
        elif self.port_name in available_ports:
            selected_port = self.port_name
            logger.info(f"Using MIDI port: {selected_port}")
        else:
            raise RuntimeError(
                f"Port '{self.port_name}' not found. Available: {available_ports}"
            )
        
        self.port = mido.open_input(selected_port)
        logger.info(f"MIDI port opened: {selected_port}")
    
    def close(self):
        """Close the MIDI input port."""
        if self.port:
            self.port.close()
            logger.info("MIDI port closed")
    
    def is_port_available(self) -> bool:
        """Check if the current port is still available."""
        if not self.port:
            return False
        
        # Get the port name that was opened
        port_name = self.port.name if hasattr(self.port, 'name') else str(self.port)
        
        # Check if it's still in the available ports list
        available = self.list_ports()
        return port_name in available
    
    def read_events(self):
        """
        Generator that yields MIDI events as they arrive.
        
        Yields:
            MidiEvent objects or None (for polling timeout)
        """
        if not self.port:
            raise RuntimeError("MIDI port not opened. Call open() first.")
        
        logger.info(f"Listening for MIDI events on channel {self.channel}...")
        
        # Track last port check time
        last_port_check = time.time()
        port_check_interval = 1.0  # Check every second
        
        # Use iter_pending() with polling to allow shutdown checks and detect disconnection
        try:
            while True:
                # Periodically check if port is still available
                current_time = time.time()
                if current_time - last_port_check >= port_check_interval:
                    if not self.is_port_available():
                        logger.error("MIDI port no longer available")
                        raise RuntimeError("MIDI device disconnected - port no longer available")
                    last_port_check = current_time
                
                # Try to read pending messages (non-blocking)
                try:
                    pending = list(self.port.iter_pending())
                except (OSError, IOError) as e:
                    # USB device disconnected
                    logger.error(f"MIDI device I/O error: {e}")
                    raise RuntimeError(f"MIDI device disconnected: {e}")
                
                if not pending:
                    # No messages, yield control and sleep
                    time.sleep(0.01)  # 10ms to avoid CPU spinning
                    yield None  # Allow shutdown checks
                    continue
                
                # Process all pending messages
                for msg in pending:
                    timestamp = time.time()
                    
                    # Filter by channel if specified
                    if self.channel > 0 and hasattr(msg, 'channel'):
                        if msg.channel + 1 != self.channel:  # mido uses 0-indexed channels
                            continue
                    
                    # Parse message type
                    if msg.type == 'note_on' and msg.velocity > 0:
                        event = MidiEvent(
                            type='note_on',
                            note=msg.note,
                            velocity=msg.velocity,
                            channel=msg.channel + 1 if hasattr(msg, 'channel') else 1,
                            timestamp=timestamp
                        )
                        logger.debug(f"MIDI event: note_on note={msg.note} velocity={msg.velocity}")
                        yield event
                    
                    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        event = MidiEvent(
                            type='note_off',
                            note=msg.note,
                            velocity=0,
                            channel=msg.channel + 1 if hasattr(msg, 'channel') else 1,
                            timestamp=timestamp
                        )
                        logger.debug(f"MIDI event: note_off note={msg.note}")
                        yield event
                    
                    elif msg.type == 'control_change':
                        event = MidiEvent(
                            type='control_change',
                            control=msg.control,
                            value=msg.value,
                            channel=msg.channel + 1 if hasattr(msg, 'channel') else 1,
                            timestamp=timestamp
                        )
                        logger.debug(f"MIDI event: CC{msg.control}={msg.value}")
                        yield event
        
        except KeyboardInterrupt:
            logger.info("MIDI read interrupted by user")
            return
    
    def detect_chord(self, event: MidiEvent) -> Optional[Set[int]]:
        """
        Check if a note_on event completes a chord.
        
        Args:
            event: MidiEvent with type='note_on'
            
        Returns:
            Set of notes in the chord, or None
        """
        if event.type == 'note_on' and event.note is not None:
            return self.chord_detector.add_note(event.note, event.timestamp)
        return None
    
    def check_double_tap(self, event: MidiEvent) -> bool:
        """
        Check if a note_on event completes a double-tap.
        
        Args:
            event: MidiEvent with type='note_on'
            
        Returns:
            True if this is the second tap, False if first tap
        """
        if event.type == 'note_on' and event.note is not None:
            return self.double_tap_tracker.on_press(event.note, event.timestamp)
        return False
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Test/demo mode
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    print("Available MIDI ports:")
    for i, port in enumerate(MidiInput.list_ports()):
        print(f"  {i}: {port}")
    
    print("\nListening for MIDI events (Ctrl+C to stop)...")
    print("Try: Play notes to see events, press same note twice quickly for double-tap\n")
    
    with MidiInput() as midi:
        try:
            for event in midi.read_events():
                if event.type == 'note_on':
                    is_second = midi.check_double_tap(event)
                    chord = midi.detect_chord(event)
                    
                    status = []
                    if is_second:
                        status.append("DOUBLE-TAP")
                    if chord:
                        status.append(f"CHORD{chord}")
                    
                    status_str = f" [{', '.join(status)}]" if status else ""
                    print(f"Note {event.note} ON (vel={event.velocity}){status_str}")
                
                elif event.type == 'note_off':
                    print(f"Note {event.note} OFF")
                
                elif event.type == 'control_change':
                    print(f"CC{event.control} = {event.value}")
        
        except KeyboardInterrupt:
            print("\nStopped.")
