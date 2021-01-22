import React, { useState, useRef, useEffect } from 'react'
import './App.css'


const Stream = ({ name, offset }) => {
  const movable = useRef(null)
  const [moving, setMoving] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const onMouseDown = (e) => {
    setMoving(true)
    e.preventDefault()
    let lastPos = [e.clientX, e.clientY]
    document.onmouseup = () => {
      setMoving(false)
      document.onmouseup = document.onmousemove = null
    }

    document.onmousemove = (e) => {
      let pos = [e.clientX, e.clientY]
      let delta = [pos[0] - lastPos[0], pos[1] - lastPos[1]]
      lastPos = pos
      movable.current.style.left = (movable.current.offsetLeft + delta[0]) + "px"
      movable.current.style.top = (movable.current.offsetTop + delta[1]) + "px"
    }
  }

  return (
    <div ref={movable} className={"movable stream" + (moving ? " moving" : "")} style={{top: offset + 30 + 'px', left: '20px'}}>
      <div class="stream-header">
        <button onClick={() => socket.send(name)}><i class="material-icons">play_arrow</i></button>
        <span class="mover stream-name" onMouseDown={onMouseDown}>{name}</span>
        <button class="expand" onClick={() => setExpanded(!expanded)}><i class="material-icons">add</i></button>
      </div>
      {expanded &&
      <div class="stream-details">
        Details go here...
      </div>}
    </div>
  )
}

let socket;

const App = () => {
  const [streams, setStreams] = useState([])

  useEffect(() => {
    socket = new WebSocket("ws://localhost:8765")
    socket.onmessage = (event) => {
      setStreams(JSON.parse(event.data))
    }
  }, [])

  return (
    <>
      <button className="refresh" onClick={() => socket.send("refresh")}><i class="material-icons">refresh</i></button>
      {streams.map((name, index) => <Stream key={name} name={name} offset={index*70} />)}
    </>
  )
}

export default App
