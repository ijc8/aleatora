import React, { useState, useRef, useEffect } from 'react'
import './App.css'

// Data from Python process: map from variable name (String) => Stream info
// Stream info: { name: String, parameters: Parameters, children: undefined or Children }
// Parameter: map from String => Stream info or String (__repr__)
// Children: { streams: [Stream info], direction: String, separator: String }

const Icon = ({ name }) => <i className="material-icons">{name}</i>

const Value = ({value}) => {
  if (Array.isArray(value) || ["number", "string", "boolean"].includes(typeof value)) {
    return JSON.stringify(value)
  }
  return <Details {...value} />
}

// TODO: cycle checking, fix styling
const Details = ({ id, name, parameters, children, implementation }) => {
  const [showImplementation, setShowImplementation] = useState(false)

  let paramFrag
  if (Object.keys(parameters).length) {
    paramFrag = <>
      <h2>Parameters</h2>
      <ul>
        {Object.entries(parameters).map(([n, p]) => <li key={n}>{n} = <Value key={n} value={p} /></li>)}
      </ul>
    </>
  }
  let childFrag
  if (children) {
    childFrag = <div className={children.direction}>
      {children.streams.map((s, i) => <Value key={i} value={s} />).reduce((prev, cur) => [prev, <div className="separator">{children.separator}</div>, cur])}
    </div>
  }
  let implFrag
  if (implementation) {
    implFrag = <>
      <h2>Implementation <button onClick={() => setShowImplementation(!showImplementation)}><Icon name={showImplementation ? 'remove' : 'add'} /></button></h2>
      {showImplementation && <div className="implementation"><Details {...implementation} /></div>}
    </>
  }
  return (<div className="node">
      <div style={{display: 'flex', justifyContent: 'space-between'}}>
        <h1>{name}</h1>
        {id !== undefined && <span className="stream-id">{id}</span>}
      </div>
      {paramFrag}{childFrag}{implFrag}
    </div>)
}

const Stream = ({ name, stream, zIndex, moveToTop, offset }) => {
  const movable = useRef(null)
  const [moving, setMoving] = useState(false)
  const [expanded, setExpanded] = useState(-1)

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
        <button className={"expand " + (expanded === 0 ? 'punched' : '')} onClick={() => setExpanded(expanded === 0 ? -1 : 0)}><Icon name="zoom_in" /></button>
        {stream.name === "envelope" && <button className={"expand " + (expanded === 1 ? 'punched' : '')} onClick={() => setExpanded(expanded === 1 ? -1 : 1)}><Icon name="insights" /></button>}
        <div className="spacer"></div>
      </div>
      {expanded === 0 &&
      <div className="stream-details">
        <Details {...stream} />
      </div>}
      {expanded === 1 && stream.name === "envelope" &&
      <EnvelopeTab points={stream.parameters.points} />}
    </div>
  )
}

const EnvelopeTab = ({ name, points }) => {
  const env = useRef(null)
  useEffect(() => {
    if (!env.current) {
      env.current = new Nexus.Envelope('#envelope', {
        points: (points === undefined ? [{x: 0, y: 0}] : points.map(([x, y]) => ({x, y})))
      })
    }
  }, [])

  return <div>
    <div class="envelope-toolbar">
      <span class="needs-better-name">... envelope duration ...</span>
      <button onClick={() => send({ cmd: "save", type: "envelope", name, payload: env.current.points })}><Icon name="save" /></button>
    </div>
    <div id="envelope" style={{border: '1px solid black', borderTop: 'none'}} />
  </div>
}

// TODO: to mirror readline, need to keep track of original and modified lines of history...
let history = ['']
let historyIndex = 0

const REPL = ({ setAppendOutput }) => {
  const textarea = useRef()
  let inputStart = useRef()

  useEffect(() => {
    textarea.current.value = ">>> "
    inputStart.current = textarea.current.value.length
  }, [])

  setAppendOutput((output) => {
    console.log("new output", output)
    const history = textarea.current.value.slice(0, inputStart.current)
    const response = output + '>>> '
    const input = textarea.current.value.slice(inputStart.current)
    textarea.current.value = history + response + input
    inputStart.current += response.length
  })

  const onKeyDown = (event) => {
    console.log("keydown", event.keyCode)
    if (event.keyCode === 8 && (textarea.current.selectionStart <= inputStart.current)) {
      event.preventDefault()
    } else if (event.keyCode === 46 && (textarea.current.selectionStart < inputStart.current)) {
      event.preventDefault()
    } else if (event.keyCode === 37 && (textarea.current.selectionStart <= inputStart.current)) {
      event.preventDefault()
    } else if (event.keyCode === 38) {
      event.preventDefault()
      if (historyIndex > 0) {
        historyIndex--
        textarea.current.value = textarea.current.value.slice(0, inputStart.current) + history[historyIndex]
      }
    } else if (event.keyCode === 40) {
      event.preventDefault()
      if (historyIndex < history.length - 1) {
        historyIndex++
        textarea.current.value = textarea.current.value.slice(0, inputStart.current) + history[historyIndex]
      }
    }
  }

  const onInput = (event) => {
    history[historyIndex] = textarea.current.value.slice(inputStart.current)
  }

  const onKeyPress = (event) => {
    console.log("keypress", event.charCode)
    if (textarea.current.selectionStart < inputStart.current || event.keyCode === 13) {
      event.preventDefault()
    }

    if (event.charCode === 13) {
      const code = textarea.current.value.slice(inputStart.current)
      console.log("Submitting user code:", code)
      send({ cmd: "exec", code })
      inputStart.current = textarea.current.value.length + 1
      console.log("sent successfully")
      if (historyIndex === history.length - 1) {
        history.push('')
        historyIndex++
      } else {
        history.splice(-1, 0, history[historyIndex])
        historyIndex = history.length - 1
      }
    }
  }

  const onPasteOrCut = (event) => {
    if (textarea.current.selectionStart <= inputStart.current) {
      event.preventDefault()
    }
  }

  return <div style={{position: 'absolute', right: 0, bottom: 0, padding: '1em'}}>
    <textarea ref={textarea} spellCheck={false}
              onKeyDown={onKeyDown} onKeyPress={onKeyPress} onPaste={onPasteOrCut} onCut={onPasteOrCut} onInput={onInput}
              style={{width: '600px', height: '300px', border: '1px solid black', resize: 'none', fontSize: '20px'}} />
  </div>
}

let socket
const Nexus = window.Nexus
const send = (obj) => socket.send(JSON.stringify(obj))

const App = () => {
  const [streams, setStreams] = useState([])
  // Used to determine stacking order in floating layout
  const [zIndices, setZIndices] = useState({})
  const appendOutput = useRef()

  useEffect(() => {
    socket = new WebSocket("ws://localhost:8765")
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === "streams") {
        setStreams(data.streams)
      } else if (data.type === "output") {
        appendOutput.current(data.output)
      }
    }
  }, [])

  return (
    <>
      <button className="refresh" onClick={() => send({ cmd: "refresh" })}><Icon name="refresh" /></button>
      {Object.entries(streams).map(([name, stream], index) => {
        return <Stream key={name}
                       name={name}
                       stream={stream}
                       zIndex={zIndices[name]}
                       moveToTop={() => setZIndices({...zIndices, [name]: Math.max(0, ...Object.values(zIndices)) + 1})}
                       offset={index*70} />
      })}
      <REPL setAppendOutput={(f) => appendOutput.current = f} />
    </>
  )
}

export default App
