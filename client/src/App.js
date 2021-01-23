import React, { useState, useRef, useEffect } from 'react'
import './App.css'

// Data from Python process: map from variable name (String) => Stream info
// Stream info: { name: String, parameters: Parameters, children: undefined or Children }
// Parameter: map from String => Stream info or String (__repr__)
// Children: { streams: [Stream info], direction: String, separator: String }

// TODO: cycle checking, fix styling
const Details = ({ name, parameters, children, implementation }) => {
  let paramFrag
  if (Object.keys(parameters).length) {
    paramFrag = <>
      <h2>Parameters:</h2>
      <ul>
        {Object.entries(parameters).map(([n, p]) => <li>{n} = {typeof p === 'string' ? p : <Details {...p} />}</li>)}
      </ul>
    </>
  }
  let childFrag
  if (children) {
    childFrag = <div className={children.direction}>{children.streams.map(s => <Details {...s} />).join(<span>{children.separator}</span>)}</div>
  }
  let implFrag
  if (implementation) {
    implFrag = <>
      <p>Implementation<button onClick={() => 0}>+</button></p>
      <div className="implementation"><Details {...implementation} /></div>
    </>
  }
  return <div className="node"><h1>{name}</h1>{paramFrag}{childFrag}{implFrag}</div>
}

const Stream = ({ name, stream, offset }) => {
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
      <div className="stream-header">
        <button onClick={() => socket.send(name)}><i className="material-icons">play_arrow</i></button>
        <span className="mover stream-name" onMouseDown={onMouseDown}>{name}</span>
        <button className="expand" onClick={() => setExpanded(!expanded)}><i className="material-icons">add</i></button>
      </div>
      {expanded &&
      <div className="stream-details">
        <Details {...stream} />
      </div>}
    </div>
  )
}

let socket

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
      <button className="refresh" onClick={() => socket.send("refresh")}><i className="material-icons">refresh</i></button>
      {Object.entries(streams).map(([name, stream], index) => <Stream key={name} name={name} stream={stream} offset={index*70} />)}
    </>
  )
}

export default App
