const audioContext = new AudioContext()

const setup = async () => {
  await audioContext.audioWorklet.addModule("worklet.js")
  const node = new AudioWorkletNode(audioContext, "my-audio-processor", { outputChannelCount: [2] })
  node.onprocessorerror = () => console.log("!!!")
  node.connect(audioContext.destination)
  return node
}

setup()

console.log("Hello")