import numpy as np
import pyvst

from .streams import stream, SAMPLE_RATE

OPEN_EDITOR = 0 # redacted, just in case
IDLE_EDITOR = 0 # redacted, just in case

class VSTEditor:
    def __init__(self, vst):
        self.vst = vst

    def open(self):
        self.vst._dispatch(OPEN_EDITOR)
    
    def idle(self):
        self.vst._dispatch(IDLE_EDITOR)

class HostedVST:
    def __init__(self, path, block_size, volume_threshold, instrument):
        self.block_size = block_size
        self.volume_threshold = volume_threshold
        self.instrument = instrument
        self.host = pyvst.SimpleHost(path, sample_rate=SAMPLE_RATE, block_size=block_size)
        self.vst = self.host.vst
        # self.vst.verbose = True
        self.ui = VSTEditor(self.vst)
    
    def __call__(self, stream):
        if self.instrument:
            return self.run_with_events(stream)
        else:
            raise NotImplementedError

    @stream
    def run_with_events(self, event_stream):
        delta_frames = 0
        for event_chunk in event_stream.chunk(self.block_size):
            vst_events = []
            for events in event_chunk:
                for event in events:
                    velocity = 0 if event.velocity is None else int(event.velocity)
                    vst_events.append(pyvst.midi.midi_note_event(note=int(event.note), velocity=velocity, kind=event.type, delta_frames=delta_frames))
                    delta_frames = 0
                delta_frames += 1
            self.vst.process_events(pyvst.midi.wrap_vst_events(vst_events))
            # TODO: Handle multiple channels.
            yield from self.vst.process(input=None, sample_frames=self.block_size)[0, :].tolist()
            self.host.transport.step(self.block_size)
        # TODO: Optional end condition, like low volume?
        while True:
            chunk = self.vst.process(input=None, sample_frames=self.block_size)[0, :]
            yield from chunk.tolist()
            self.host.transport.step(self.block_size)
            if self.volume_threshold is not None:
                rms = np.sqrt((chunk ** 2).mean())
                if rms < self.volume_threshold:
                    return

def load_vsti(path, block_size=512, volume_threshold=2e-6):
    return HostedVST(path, block_size, volume_threshold=volume_threshold, instrument=True)
