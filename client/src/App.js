import React, { useState, useRef, useEffect } from 'react'
import './App.css'

// Data from Python process: map from variable name (String) => Stream info
// Stream info: { name: String, parameters: Parameters, children: undefined or Children }
// Parameter: map from String => Stream info or String (__repr__)
// Children: { streams: [Stream info], direction: String, separator: String }

const Icon = ({ name }) => <i className="material-icons">{name}</i>

// TODO: cycle checking, fix styling
const Details = ({ name, parameters, children, implementation }) => {
  const [showImplementation, setShowImplementation] = useState(false)

  let paramFrag
  if (Object.keys(parameters).length) {
    paramFrag = <>
      <h2>Parameters</h2>
      <ul>
        {Object.entries(parameters).map(([n, p]) => <li key={n}>{n} = {typeof p === 'string' ? p : <Details {...p} />}</li>)}
      </ul>
    </>
  }
  let childFrag
  if (children) {
    childFrag = <div className={children.direction}>
      {children.streams.map(s => <Details {...s} />).reduce((prev, cur) => [prev, <div className="separator">{children.separator}</div>, cur])}
    </div>
  }
  let implFrag
  if (implementation) {
    implFrag = <>
      <h2>Implementation <button onClick={() => setShowImplementation(!showImplementation)}><Icon name={showImplementation ? 'remove' : 'add'} /></button></h2>
      {showImplementation && <div className="implementation"><Details {...implementation} /></div>}
    </>
  }
  return <div className="node"><h1>{name}</h1>{paramFrag}{childFrag}{implFrag}</div>
}

const Stream = ({ name, stream, zIndex, moveToTop, offset }) => {
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
    <div ref={movable} onMouseDown={moveToTop} className={"movable stream" + (moving ? " moving" : "")} style={{top: offset + 30 + 'px', left: '20px', zIndex}}>
      <div className={"stream-header " + (expanded ? "expanded" : "")}>
        <button onClick={() => socket.send(name)}><Icon name="play_arrow" /></button>
        <span className="mover stream-name" onMouseDown={onMouseDown}>{name}</span>
        <button className={"expand " + (expanded ? 'punched' : '')} onClick={() => setExpanded(!expanded)}><Icon name="zoom_in" /></button>
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
  // Used to determine stacking order in floating layout
  const [zIndices, setZIndices] = useState({})

  useEffect(() => {
    socket = new WebSocket("ws://localhost:8765")
    socket.onmessage = (event) => {
      setStreams(JSON.parse(event.data))
    }
  }, [])

  return (
    <>
      <button className="refresh" onClick={() => socket.send("refresh")}><Icon name="refresh" /></button>
      {Object.entries(streams).map(([name, stream], index) => {
        return <Stream key={name}
                       name={name}
                       stream={stream}
                       zIndex={zIndices[name]}
                       moveToTop={() => setZIndices({...zIndices, [name]: Math.max(0, ...Object.values(zIndices)) + 1})}
                       offset={index*70} />
      })}
    </>
  )
}

export default App
