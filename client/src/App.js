import React, { useState, useRef, useEffect } from 'react'
import './App.css'

// Data from Python process: map from variable name (String) => Stream info
// Stream info: { name: String, parameters: Parameters, children: undefined or Children }
// Parameter: map from String => Stream info or String (__repr__)
// Children: { streams: [Stream info], direction: String, separator: String }

const Icon = ({ name, style }) => <i className="material-icons" style={style}>{name}</i>

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
  if (parameters !== undefined && Object.keys(parameters).length) {
    paramFrag = <>
      <h2>Parameters</h2>
      <ul className="parameter-list">
        {Object.entries(parameters).map(([n, p]) => <li key={n}>{n} = <Value key={n} value={p} /></li>)}
      </ul>
    </>
  }
  let childFrag
  if (children) {
    childFrag = <div className={children.direction}>
      {children.streams.map((s, i) => <Value key={i} value={s} />).reduce((prev, cur) => [prev, <div key={"sep-" + prev.key} className="separator">{children.separator}</div>, cur])}
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

const InspectorTab = ({ name, stream }) => <Details {...stream} />

InspectorTab.icon = "zoom_in"

const EnvelopeTab = ({ name, stream }) => {
  const env = useRef(null)
  const points = stream.parameters.points
  useEffect(() => {
    if (!env.current) {
      env.current = new Nexus.Envelope('#envelope', {
        points: (points === undefined ? [{x: 0, y: 0}] : points.map(([x, y]) => ({x, y})))
      })
    }
  }, [])

  return <div>
    <div className="envelope-toolbar">
      <span className="needs-better-name">... envelope duration ...</span>
      <button onClick={() => send({ cmd: "save", type: "envelope", name, payload: env.current.points })}><Icon name="save" /></button>
    </div>
    <div id="envelope" />
  </div>
}

EnvelopeTab.icon = "insights"

const SequenceTab = ({ name, stream }) => {
  const roll = useRef(null)
  const onKeyPress = (event) => {
    if (event.charCode === KEY_ENTER) {
      console.log(roll.current.sequence)
      send({ cmd: "save", type: "sequence", name, payload: roll.current.sequence })
    }
  }

  useEffect(() => {
    roll.current.sequence = stream.parameters.notes.map(([start, length, pitch]) => ({t: start, g: length, n: pitch}))
    roll.current.redraw()
  })

  return <webaudio-pianoroll ref={roll} onKeyPress={onKeyPress} width="498" wheelzoom="1" editmode="dragpoly" colrulerbg="#fff" colrulerfg="#000" colrulerborder="#fff" xruler="20" yruler="20" xscroll="1" yscroll="1"></webaudio-pianoroll>
}

SequenceTab.icon = "piano"

const SpeechTab = ({ name, stream }) => {
  const textbox = useRef()
  const onKeyPress = (event) => {
    if (event.charCode === KEY_ENTER && event.ctrlKey) {
      send({ cmd: "save", type: "speech", name, payload: textbox.current.value })
    }
  }
  return <textarea ref={textbox} className="speech" type="text" defaultValue={stream.parameters.text} onKeyPress={onKeyPress} />
}

SpeechTab.icon = "chat"

// For now, this is many-to-one; later it might be many-to-many.
const tabMap = {
  "envelope": EnvelopeTab,
  "sequence": SequenceTab,
  "speech": SpeechTab,
}

const Stream = ({ name, stream, zIndex, moveToTop, offset, finished }) => {
  // TODO: Separate widget for Instruments.
  const movable = useRef(null)
  const [moving, setMoving] = useState(false)
  const [expanded, setExpanded] = useState(-1)
  const [playing, setPlaying] = useState(false)

  if (playing && finished) {
    setPlaying(false)
  }

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

  let tabs = [InspectorTab]
  if (tabMap[stream.name] !== undefined) {
    tabs.push(tabMap[stream.name])
  }

  return (
    <div ref={movable} onMouseDown={moveToTop} className={"movable stream" + (moving ? " moving" : "")} style={{top: offset[0] + 'px', left: offset[1] + 'px', zIndex}}>
      <div className={"stream-header " + (expanded ? "expanded" : "")} onMouseDown={onMouseDown}>
        <button className="control" onClick={() => {
          send({ cmd: "rewind", name })
        }}>
          <Icon name="history" />
        </button>
        <button className="control" style={{borderLeft: 'none'}} onClick={() => {
          send({ cmd: playing ? "pause" : "play", name })
          setPlaying(!playing)
        }}>
          <Icon name={playing ? "pause" : "play_arrow"} />
        </button>
        {stream.type === 'instrument' &&
        <button className="control" style={{borderLeft: 'none'}} onClick={() => send({ cmd: "record", name })}>
          <Icon name="fiber_manual_record" style={{color: "red", fontSize: "18px", paddingLeft: "2px", paddingBottom: "1px"}} />
        </button>}
        <button className="control" style={{borderLeft: 'none'}} onClick={() => {
          send({ cmd: "stop", name })
          setPlaying(false)
        }}>
          <Icon name="stop" />
        </button>
        <span className="stream-name">{name}</span>
        {tabs.map((tab, i) =>
          <button key={i}
                  className={"tab control " + (expanded === i ? 'punched' : '')}
                  onClick={() => setExpanded(expanded === i ? -1 : i)}
                  style={i === tabs.length - 1 ? {} : {borderRight: 'none'}}>
            <Icon name={tab.icon} />
          </button>
        )}
        <div className="spacer"></div>
      </div>
      {expanded >= 0 && (() => {
        const Tab = tabs[expanded]
        return <div className="stream-details"><Tab name={name} stream={stream} /></div>
      })()}
    </div>
  )
}

let history = [{original: '', modified: ''}]
let historyIndex = 0

const KEY_BACKSPACE = 8
const KEY_ENTER = 13
const KEY_HOME = 36
const KEY_LEFT = 37
const KEY_UP = 38
const KEY_DOWN = 40
const KEY_DELETE = 46

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
    if (event.keyCode === KEY_BACKSPACE && (textarea.current.selectionStart <= inputStart.current)) {
      event.preventDefault()
    } else if (event.keyCode === KEY_DELETE && (textarea.current.selectionStart < inputStart.current)) {
      event.preventDefault()
    } else if (event.keyCode === KEY_LEFT && (textarea.current.selectionStart <= inputStart.current)) {
      event.preventDefault()
    } else if (event.keyCode === KEY_HOME) {
      event.preventDefault()
      textarea.current.selectionStart = inputStart.current
      if (!event.shiftKey) textarea.current.selectionEnd = inputStart.current
    } else if (event.keyCode === KEY_UP) {
      event.preventDefault()
      if (historyIndex > 0) {
        historyIndex--
        textarea.current.value = textarea.current.value.slice(0, inputStart.current) + history[historyIndex].modified
      }
    } else if (event.keyCode === KEY_DOWN) {
      event.preventDefault()
      if (historyIndex < history.length - 1) {
        historyIndex++
        textarea.current.value = textarea.current.value.slice(0, inputStart.current) + history[historyIndex].modified
      }
    }
  }

  const onInput = (event) => {
    history[historyIndex].modified = textarea.current.value.slice(inputStart.current)
  }

  const onKeyPress = (event) => {
    console.log("keypress", event.charCode)
    if (textarea.current.selectionStart < inputStart.current || event.keyCode === 13) {
      event.preventDefault()
    }

    if (event.charCode === KEY_ENTER) {
      textarea.current.selectionStart = textarea.current.selectionEnd = textarea.current.value.length
      const code = textarea.current.value.slice(inputStart.current)
      console.log("Submitting user code:", code)
      send({ cmd: "exec", code })
      inputStart.current = textarea.current.value.length + 1
      console.log("sent successfully")
      history[history.length - 1].original = history[history.length - 1].modified = history[historyIndex].modified
      history[historyIndex].modified = history[historyIndex].original
      history.push({original: '', modified: ''})
      historyIndex = history.length - 1
    }
  }

  const onPasteOrCut = (event) => {
    if (textarea.current.selectionStart < inputStart.current) {
      event.preventDefault()
    }
  }

  return <div style={{position: 'absolute', right: 0, bottom: 0, padding: '1em'}}>
    <textarea ref={textarea} spellCheck={false}
              onKeyDown={onKeyDown} onKeyPress={onKeyPress} onPaste={onPasteOrCut} onCut={onPasteOrCut} onInput={onInput}
              style={{width: '600px', height: '300px', border: '1px solid black', resize: 'none', fontSize: '20px'}} />
  </div>
}

const filterTree = (tree, filter) => {
  const filtered = {}
  Object.entries(tree).forEach(([name, value]) => {
    if (typeof(value) === 'object') {
      const subtree = filterTree(value, filter)
      if (Object.keys(subtree).length) {
        filtered[name] = subtree
      }
    } else if (name.includes(filter)) {
      filtered[name] = value
    }
  })
  return filtered
}

const Resource = ({ name, value }) => {
  return <li><span className="resource-name">{name} - {value}</span></li>
}

const Module = ({ name, resources, expand, setExpand }) => (
  <li>
    <div className="module-header">
      <button className="module-toggle" onClick={() => setExpand(!expand)}><Icon name={`expand_${expand ? 'less' : 'more'}`} /></button>
      <span className="module-name">{name}</span>
    </div>
    {expand &&
    <ul className="resource-list">
      {Object.entries(resources).map(([name, value]) => <Resource key={name} name={name} value={value} />)}
    </ul>}
  </li>
)

const ResourcePane = ({ resources }) => {
  const [filter, setFilter] = useState("")
  const [expand, setExpand] = useState({})
  resources = filterTree(resources, filter)
  return <div className="resource-pane">
    <input type="text" placeholder="Filter resources" value={filter} onChange={(e) => setFilter(e.target.value)} />
    <ul className="module-list">
      {Object.entries(resources).map(([name, value]) =>
        <Module key={name} name={name} resources={value} expand={expand[name] === undefined ? true : expand[name]} setExpand={(e) => setExpand({ ...expand, [name]: e })} />)}
    </ul>
  </div>
}

const VolumeControl = ({ setVolume }) => {
  const [volume, _setVolume] = useState(-6)
  return <>
    <div style={{position: 'absolute', top: '40px', left: '10px', textAlign: 'center', width: '40px'}}>
      <div>{volume}</div>
      <input style={{writingMode: 'vertical-lr'}} type="range" min="-72" max="12"
             onChange={(e) => { setVolume(e.target.value); _setVolume(e.target.value) }} value={volume}></input>
    </div>
  </>
}

const Settings = ({ doRefresh }) => {
  return <div className="settings">
    <h2>Settings</h2>
    <button className="refresh" onClick={doRefresh}>Refresh <Icon name="refresh" /></button>
    <label>Remember <input id="rewind-time" type="number" defaultValue="1" disabled></input> second</label>
    <label>Rewind by &nbsp;<input id="rewind-time" type="number" defaultValue="1" disabled></input> second</label>
    <label>Diverge after rewind <input type="checkbox" defaultChecked="true" disabled></input></label>
  </div>
}

let socket
const Nexus = window.Nexus
const send = (obj) => socket.send(JSON.stringify(obj))

const App = () => {
  const [streams, setStreams] = useState([])
  const [resources, setResources] = useState({})
  // Used to determine stacking order in floating layout
  const [zIndices, setZIndices] = useState({})
  const appendOutput = useRef()
  const [finished, setFinished] = useState(null)

  useEffect(() => {
    socket = new WebSocket("ws://localhost:8765")
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === "resources") {
        // TODO: s/streams/resources/g
        setStreams(data.resources_old)
        setResources(data.resources)
      } else if (data.type === "output") {
        appendOutput.current(data.output)
      } else if (data.type === "finish") {
        setFinished(data.name)
        setFinished(null)
      }
    }
  }, [])

  return (
    <>
      <Settings doRefresh={() => send({ cmd: "refresh" })} />
      <ResourcePane resources={resources} />
      {Object.entries(streams).map(([name, stream], index) => {
        return <Stream key={name}
                       name={name}
                       stream={stream}
                       zIndex={zIndices[name]}
                       moveToTop={() => setZIndices({...zIndices, [name]: Math.max(0, ...Object.values(zIndices)) + 1})}
                       offset={[index*70 + 30, 320]}
                       finished={name === finished} />
      })}
      <REPL setAppendOutput={(f) => appendOutput.current = f} />
      <VolumeControl setVolume={(db) => send({ cmd: "volume", volume: Math.pow(10, db/20) })} />
    </>
  )
}

export default App
