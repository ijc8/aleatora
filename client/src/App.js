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
        {Object.entries(parameters).map(([n, p]) => <li key={n}>{n} = {p.name === undefined ? p : <Details {...p} />}</li>)}
      </ul>
    </>
  }
  let childFrag
  if (children) {
    childFrag = <div className={children.direction}>
      {children.streams.map((s, i) => <Details key={i} {...s} />).reduce((prev, cur) => [prev, <div className="separator">{children.separator}</div>, cur])}
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

  // Implement dragging.
  const onMouseDown = (e) => {
    let moved = false
    // Commented out so buttons in the title bar still press down on drag.
    // May eventually want to make them inactive again after movement (e.g. how GNOME's WM does it).
    // e.preventDefault()
    let lastPos = [e.clientX, e.clientY]
    document.onmouseup = () => {
      document.onmouseup = document.onmousemove = null
      if (moved) {
        // Don't register the drag as a click.
        const captureClick = (e) => {
          e.stopPropagation()
          window.removeEventListener('click', captureClick, true)
        }
        window.addEventListener('click', captureClick, true)
      }
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
        movable.current.style.left = (movable.current.offsetLeft + delta[0]) + "px"
        movable.current.style.top = (movable.current.offsetTop + delta[1]) + "px"
        lastPos = pos
      }
    }
  }

  return (
    <div ref={movable} onMouseDown={moveToTop} className={"movable stream" + (moving ? " moving" : "")} style={{top: offset + 30 + 'px', left: '20px', zIndex}}>
      <div className={"stream-header " + (expanded ? "expanded" : "")} onMouseDown={onMouseDown}>
        <button onClick={() => send({ cmd: "play", name })}><Icon name="play_arrow" /></button>
        <span className="stream-name">{name}</span>
        <button className={"expand " + (expanded ? 'punched' : '')} onClick={() => setExpanded(!expanded)}><Icon name="zoom_in" /></button>
        <div className="spacer"></div>
      </div>
      {expanded &&
      <div className="stream-details">
        <Details {...stream} />
      </div>}
    </div>
  )
}

const Envelope = ({ name, points }) => {
  // TODO: Make this less hacky, reduce duplication with Stream.
  const env = useRef(null)
  useEffect(() => {
    if (!env.current) {
      env.current = new Nexus.Envelope('#envelope', {
        points: (points === undefined ? [{x: 0, y: 0}] : points.map(([x, y]) => ({x, y})))
      })
      env.current.on('change', console.log)
    }
  }, [])

  const movable = useRef(null)
  const [moving, setMoving] = useState(false)

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

  return <div ref={movable} className="stream movable">
    <div className="stream-header" style={{width: '100%', borderBottom: '1px solid black'}} onMouseDown={onMouseDown}>
      <button onClick={() => send({ cmd: "save", type: "envelope", name, payload: env.current.points })}><Icon name="save" /></button>
      <span className="stream-name" style={{width: '100%', borderRight: '1px solid black'}}>{name}</span>
    </div>
    <div id="envelope" style={{border: '1px solid black', borderTop: 'none'}}></div>
  </div>
}

let socket
const Nexus = window.Nexus
const send = (obj) => socket.send(JSON.stringify(obj))

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
      <button className="refresh" onClick={() => send({ cmd: "refresh" })}><Icon name="refresh" /></button>
      {Object.entries(streams).map(([name, stream], index) => {
        if (stream.name === "envelope") {
          return <Envelope key={name} name={name} points={stream.parameters.points} />
        } else {
          return <Stream key={name}
                        name={name}
                        stream={stream}
                        zIndex={zIndices[name]}
                        moveToTop={() => setZIndices({...zIndices, [name]: Math.max(0, ...Object.values(zIndices)) + 1})}
                        offset={index*70} />
        }
      })}
    </>
  )
}

export default App
