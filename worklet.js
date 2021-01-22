const osc = (freq, phase = 0) => {
  return () => [Math.sin(phase), osc(freq, phase + 2 * Math.PI * freq / sampleRate)];
}

const slice = (stream, stop) => {
  return () => {
    if (stop === 0) {
      return { value: stream }
    }
    const [value, next] = stream()
    return [value, slice(next, stop - 1)]
  }
}

const concat = (streams) => {
  return () => {
    if (streams.length === 0)
      return {}
    const [stream, ...rest] = streams
    const ret = stream()
    if (!Array.isArray(ret))
      return concat(rest)()
    const [value, next] = ret
    return [value, concat([next, ...rest])]
  }
}

const silence = () => [0, silence]

class MyAudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.stream = concat([slice(osc(440), 44100), slice(osc(660), 44100)])
    // this.stream = silence
  }

  process(inputs, outputs, parameters) {
    const speakers = outputs[0]

    let next = this.stream
    let value
    for (let i = 0; i < speakers[0].length; i++) {
      const ret = next()
      if (!Array.isArray(ret))
        break;
      [value, next] = ret
      speakers[0][i] = value
      speakers[1][i] = value
    }
    this.stream = next

    return true
  }
}

registerProcessor("my-audio-processor", MyAudioProcessor)
