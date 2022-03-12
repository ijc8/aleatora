import React, { useEffect, useRef, useState } from 'react';
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

function History({ value, onChange }: { value: number, onChange: any }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const width = 400
  const height = 200

  const values = useRef(new Array(100).fill(0))

  const toX = (value: number) => (value / values.current.length) * width
  const toY = (value: number) => (1 - value) / 2 * (height - 1)

  useEffect(() => {
    if (!canvas.current) return
    const context = canvas.current.getContext("2d")!
    values.current.shift()
    values.current.push(value)
    context.clearRect(0, 0, 400, 200)
    context.beginPath()
    context.moveTo(toX(0), toY(values.current[0]))
    for (let i = 1; i < values.current.length; i++) {
      context.lineTo(toX(i), toY(values.current[i]))
    }
    context.stroke()
  }, [value])
  
  return <canvas ref={canvas} width={width} height={height} />
}

function Table({ value, onChange }: { value: number[], onChange: (x: number[]) => void }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const moveData = useRef(null as { index: number, value: number } | null)
  const width = 400
  const height = 200

  const values = useRef(new Array(100).fill(0))

  const toX = (value: number) => (value / values.current.length) * width
  const toY = (value: number) => (1 - value) / 2 * (height - 1)

  const draw = () => {
    if (!canvas.current) return
    const context = canvas.current.getContext("2d")!
    context.clearRect(0, 0, 400, 200)
    context.beginPath()
    context.moveTo(toX(0), toY(values.current[0]))
    for (let i = 1; i < values.current.length; i++) {
      context.lineTo(toX(i), toY(values.current[i]))
    }
    context.stroke()
  }

  const getIndexAndValue = (e: React.MouseEvent | MouseEvent) => {
    const { left, top } = canvas.current!.getBoundingClientRect()
    const x = e.clientX - left
    const y = e.clientY - top
    const index = Math.round(x / width * (values.current.length - 1))
    const value = -(y / height * 2 - 1)
    return [
      Math.max(0, Math.min(index, values.current.length - 1)),
      Math.max(-1, Math.min(value, 1)),
    ]
  }

  const onMouseDown = (e: React.MouseEvent) => {
    const [index, value] = getIndexAndValue(e)
    values.current[index] = value
    onChange(values.current)
    console.log(values.current)
    moveData.current = { index, value }
    requestAnimationFrame(draw)

    const onMouseMove = (e: MouseEvent) => {
      if (moveData.current) {
        const old = moveData.current
        const [index, value] = getIndexAndValue(e)
        for (let i = old.index; i !== index; i += Math.sign(index - old.index)) {
          values.current[i] = old.value + (value - old.value) * (i - old.index) / (index - old.index)
        }
        values.current[index] = value
        onChange(values.current)
        moveData.current = { index, value }
        requestAnimationFrame(draw)
      }
    }
  
    const onMouseUp = (e: MouseEvent) => {
      moveData.current = null
      window.removeEventListener("mousemove", onMouseMove)
      window.removeEventListener("mouseup", onMouseUp)
    }

    window.addEventListener("mousemove", onMouseMove)
    window.addEventListener("mouseup", onMouseUp)
  }
  
  return <canvas ref={canvas} width={width} height={height} onMouseDown={onMouseDown} />
}

const Container = ({ name, type, args, value, onChange }:
    { name: string, type: string, args: any, value: any, onChange: any }) => {
  // TODO: Separate widget for Instruments.
  const movable = useRef<HTMLDivElement>(null)
  const [moving, setMoving] = useState(false)

  const Widget = (WIDGETS as any)[type] as any

  // Implement dragging.
  const onMouseDown = (e: React.MouseEvent) => {
    let moved = false
    // Commented out so buttons in the title bar still press down on drag.
    // May eventually want to make them inactive again after movement (e.g. how GNOME's WM does it).
    // e.preventDefault()
    let lastPos = [e.clientX, e.clientY]
    document.onmouseup = () => {
      document.onmouseup = document.onmousemove = null
      setMoving(false)
    }

    document.onmousemove = (e) => {
      const pos = [e.clientX, e.clientY]
      const delta = [pos[0] - lastPos[0], pos[1] - lastPos[1]]
      if (!moved && (Math.abs(delta[0]) > 3 || Math.abs(delta[1]) > 3)) {
        setMoving(true)
        moved = true
      }
      
      if (moved) {
        movable.current!.style.left = (movable.current!.offsetLeft + delta[0]) + "px"
        movable.current!.style.top = (movable.current!.offsetTop + delta[1]) + "px"
        lastPos = pos
      }
    }
  }

  return (
    <div ref={movable} className={"movable widget" + (moving ? " moving" : "")}>
      <div className="widget-header" onMouseDown={onMouseDown}>
        {name}
      </div>
      <Widget value={value} onChange={onChange} {...args} />
    </div>
  )
}

const WIDGETS = { Text, Number, Slider, History, Table }

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

  return <div>
    <h1>Aleatora Widgets</h1>
    {Object.entries(state).map(([key, { type, direction, args, value }]) => {
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
        <Container name={key} type={type} value={value} args={args} onChange={onChange} />
      </label>
    })}
  </div>
}

export default App
