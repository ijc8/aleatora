import { createSlice, combineReducers, configureStore } from '@reduxjs/toolkit';

// This should probably be handled by Redux middleware. Alas.
let socket = new WebSocket("ws://localhost:8765")
const send = (obj) => socket.send(JSON.stringify(obj))

const repl = createSlice({
  name: 'repl',
  initialState: {
    contents: ">>> ",
    inputStart: 4,
  },
  reducers: {
    setContents(state, { payload }) {
      state.contents = payload
    },
    setInputStart(state, { payload }) {
      state.inputStart = payload
    },
    appendOutput(state, { payload }) {
      console.log("new output", payload)
      const history = state.contents.slice(0, state.inputStart)
      const response = payload + '>>> '
      const input = state.contents.slice(state.inputStart)
      state.contents = history + response + input
      state.inputStart += response.length
    },
    runCode(state, { payload: code }) {
      console.log("new input", code)
      const history = state.contents.slice(0, state.inputStart)
      const input = state.contents.slice(state.inputStart)
      state.contents = history + code + "\n" + input
      state.inputStart = state.inputStart + code.length + 1
      console.log("Submitting editor code:", code)
      send({ cmd: "exec", mode: code.includes('\n') ? "exec" : "single", code })
    }
  }
})

const selectContents = state => state.repl.contents
const selectInputStart = state => state.repl.inputStart

const replActions = { selectContents, selectInputStart, ...repl.actions }
export { replActions as repl, socket, send }

const reducer = combineReducers({ repl: repl.reducer })

export default configureStore({ reducer })
