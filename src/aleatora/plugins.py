import numpy as np
import pyvst

from .streams import stream, SAMPLE_RATE

def load_vsti(path, block_size=512, volume_threshold=2e-6):
    @stream
    def instrument(event_stream):
        host = pyvst.SimpleHost(path, sample_rate=SAMPLE_RATE, block_size=block_size)
        delta_frames = 0
        for event_chunk in event_stream.chunk(block_size):
            vst_events = []
            for events in event_chunk:
                for event in events:
                    velocity = 0 if event.velocity is None else int(event.velocity)
                    vst_events.append(pyvst.midi.midi_note_event(note=int(event.note), velocity=velocity, kind=event.type, delta_frames=delta_frames))
                    delta_frames = 0
                delta_frames += 1
            host.vst.process_events(pyvst.midi.wrap_vst_events(vst_events))
            # TODO: Handle multiple channels.
            yield from host.vst.process(input=None, sample_frames=block_size)[0, :].tolist()
            host.transport.step(block_size)
        # TODO: Optional end condition, like low volume?
        while True:
            chunk = host.vst.process(input=None, sample_frames=block_size)[0, :]
            yield from chunk.tolist()
            host.transport.step(block_size)
            if volume_threshold is not None:
                rms = np.sqrt((chunk ** 2).mean())
                if rms < volume_threshold:
                    return
    return instrument
