import React, { useEffect, useState } from 'react';
import './App.css';

let socket = new WebSocket("ws://localhost:8765")
const send = (obj: any) => socket.send(JSON.stringify(obj))

window.onbeforeunload = () => {
  socket.onclose = () => {}
  socket.close()
}

function Text({ value, onChange }: { value: string, onChange?: (x: string) => void }) {
  return <input type="text" value={value ?? ""} onChange={e => onChange?.(e.target.value)} readOnly={onChange === undefined} />
}

function Number({ value, onChange }: { value: number, onChange?: (x: number) => void }) {
  return <input type="number" value={value} onChange={e => onChange?.(+e.target.value)} readOnly={onChange === undefined} />
}

function Slider({ min, max, value, onChange }:
    { min: number, max: number, value: number, onChange?: (x: number) => void }) {
  return <input type="range" min={min} max={max} value={value} step="any" onChange={e => onChange?.(+e.target.value)} readOnly={onChange === undefined} />
}

const WIDGETS = { Text, Number, Slider }

interface Widget {
  type: keyof typeof WIDGETS
  direction: "source" | "sink"
  args: { [key: string]: any }
  value: any
}

function App() {
  const [state, setState] = useState({} as { [key: string]: Widget })

  useEffect(() => {
    socket.onmessage = e => {
      const data = JSON.parse(e.data)
      if (data.type === "widgets") {
        setState(state => {
          const newState = data.payload
          for (const k of Object.keys(newState)) {
            if (state[k]) {
              newState[k].value = state[k].value
            }
          }
          console.log(newState)
          return newState
        })
      } else if (data.type === "updates") {
        setState(state => {
          const newState = Object.assign({}, state)
          for (const [k, v] of Object.entries(data.payload)) {
            if (k in newState) {
              newState[k].value = v
            }
          }
          return newState
        })
      }
    }
  }, [])

  return <div className="App">
    {Object.entries(state).map(([key, { type, direction, args, value }]) => {
      const Widget = WIDGETS[type] as any
      let onChange = undefined
      if (direction === "source") {
        onChange = (value: any) => {
          setState(state => {
            const newState = Object.assign({}, state)
            newState[key].value = value
            send({ [key]: value })
            return newState
          })
        }
      }
      return <label key={key}>
        {key}<br/>
        <Widget key={key} value={value + ""} onChange={onChange} {...args} />
      </label>
    })}
  </div>
}

export default App
