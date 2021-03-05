import React, { useState, useRef, useEffect } from 'react'
import Editor from "@monaco-editor/react";
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

const InspectorTab = ({ name, resource }) => <Details {...resource} />

InspectorTab.icon = "zoom_in"

const HelpTab = ({ name, resource }) => {
  return <ul>
    <li>Type: {resource.type}</li>
    <li>Docstring: TODO</li>
  </ul>
}

HelpTab.icon = "help_outline"

const EnvelopeTab = ({ name, resource }) => {
  const env = useRef(null)
  const points = resource.parameters.points
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

const SequenceTab = ({ name, resource }) => {
  const roll = useRef(null)
  const onKeyPress = (event) => {
    if (event.charCode === KEY_ENTER) {
      console.log(roll.current.sequence)
      send({ cmd: "save", type: "sequence", name, payload: roll.current.sequence })
    }
  }

  useEffect(() => {
    roll.current.sequence = resource.parameters.notes.map(([start, length, pitch]) => ({t: start, g: length, n: pitch}))
    roll.current.redraw()
  })

  return <webaudio-pianoroll ref={roll} onKeyPress={onKeyPress} width="498" wheelzoom="1" editmode="dragpoly" colrulerbg="#fff" colrulerfg="#000" colrulerborder="#fff" xruler="20" yruler="20" xscroll="1" yscroll="1"></webaudio-pianoroll>
}

SequenceTab.icon = "piano"

const SpeechTab = ({ name, resource }) => {
  const textbox = useRef()
  const onKeyPress = (event) => {
    if (event.charCode === KEY_ENTER && event.ctrlKey) {
      send({ cmd: "save", type: "speech", name, payload: textbox.current.value })
    }
  }
  return <textarea ref={textbox} className="speech" type="text" defaultValue={resource.parameters.text} onKeyPress={onKeyPress} />
}

SpeechTab.icon = "chat"

// For now, this is many-to-one; later it might be many-to-many.
const tabMap = {
  "envelope": EnvelopeTab,
  "sequence": SequenceTab,
  "speech": SpeechTab,
}

const Stream = ({ name, stream, finished }) => {
  // TODO: Separate widget for Instruments.
  const [expanded, setExpanded] = useState(-1)
  const [playing, setPlaying] = useState(false)

  if (playing && finished) {
    setPlaying(false)
  }

  let tabs = [InspectorTab]
  console.log(stream)
  if (tabMap[stream.name] !== undefined) {
    tabs.push(tabMap[stream.name])
  }
  tabs.push(HelpTab)

  return (
    <div className="resource-details">
      <div className="resource-controls">
        <button className="resource-control" style={{borderLeft: 'none'}} onClick={() => {
          send({ cmd: "rewind", name })
        }}>
          <Icon name="history" />
        </button>
        <button className="resource-control" onClick={() => {
          send({ cmd: playing ? "pause" : "play", name })
          setPlaying(!playing)
        }}>
          <Icon name={playing ? "pause" : "play_arrow"} />
        </button>
        {stream.type === 'instrument' &&
        <button className="resource-control" onClick={() => send({ cmd: "record", name })}>
          <Icon name="fiber_manual_record" style={{color: "red", fontSize: "18px", paddingLeft: "2px", paddingBottom: "1px"}} />
        </button>}
        <button className="resource-control" style={{borderRight: '1px solid black'}} onClick={() => {
          send({ cmd: "stop", name })
          setPlaying(false)
        }}>
          <Icon name="stop" />
        </button>
        <div className="flex-spacer">Maybe seek controls go here?</div>
        {tabs.map((tab, i) =>
          <button key={i}
                  className={"resource-control " + (expanded === i ? 'punched' : '')}
                  onClick={() => setExpanded(i)}
                  style={i === tabs.length - 1 ? {} : {borderRight: 'none'}}>
            <Icon name={tab.icon} />
          </button>
        )}
      </div>
      {expanded >= 0 && (() => {
        const Tab = tabs[expanded]
        return <div className="resource-content"><Tab name={name} resource={stream} /></div>
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

const REPL = ({ setAppendOutput, setRunCode }) => {
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
    // Scroll to the new prompt.
    textarea.current.scrollTop = textarea.current.scrollHeight
  })

  setRunCode((code) => {
    console.log("new input", code)
    const history = textarea.current.value.slice(0, inputStart.current)
    const input = textarea.current.value.slice(inputStart.current)
    textarea.current.value = history + code + "\n" + input
    inputStart.current += code.length + 1
    // Scroll to the new prompt.
    textarea.current.scrollTop = textarea.current.scrollHeight
    console.log("Submitting editor code:", code)
    send({ cmd: "exec", code })
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
      console.log("Submitting REPL code:", code)
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

  return <textarea ref={textarea} spellCheck={false} onKeyDown={onKeyDown} onKeyPress={onKeyPress} onPaste={onPasteOrCut} onCut={onPasteOrCut} onInput={onInput} />
}

const filterResources = (modules, filter) => {
  const filtered = {}
  Object.entries(modules).forEach(([name, resources]) => {
    resources = Object.assign(...Object.entries(resources).filter(([name, value]) => name.includes(filter)).map(([name, value]) => ({ [name]: value })), {})
    if (Object.keys(resources).length) {
      filtered[name] = resources
    }
  })
  return filtered
}

const Resource = ({ name, value, focus, setFocus }) => {
  const icons = {stream: "water", instrument: "piano", function: "microwave"}
  return <li onClick={setFocus} className={focus ? "focused" : ""}><span className="resource-name"><Icon name={icons[value.type]} /> {name}</span></li>
}

const Module = ({ name, resources, expand, setExpand, focus, setFocus }) => (
  <li>
    <div className="module-header">
      <button className="module-toggle" onClick={() => setExpand(!expand)}><Icon name={`expand_${expand ? 'less' : 'more'}`} /></button>
      <span className="module-name">{name}</span>
    </div>
    {expand &&
    <ul className="resource-list">
      {Object.entries(resources).map(([resourceName, value]) => {
        const fullName = `${name}.${resourceName}`
        return <Resource key={resourceName} name={resourceName} value={value} focus={focus === fullName} setFocus={() => setFocus(fullName)} />
      })}
    </ul>}
  </li>
)

const ResourcePane = ({ resources, focus, setFocus }) => {
  const [filter, setFilter] = useState("")
  const [expand, setExpand] = useState({})
  resources = filterResources(resources, filter)
  return <>
    <div className="search">
      <input type="text" placeholder="Filter resources" value={filter} onChange={(e) => setFilter(e.target.value)} />
    </div>
    <div className="resources">
      <ul className="module-list">
        {Object.entries(resources).map(([name, value]) =>
          <Module key={name} name={name} resources={value} expand={expand[name] === undefined ? true : expand[name]} setExpand={(e) => setExpand({ ...expand, [name]: e })} focus={focus} setFocus={setFocus} />)}
      </ul>
    </div>
  </>
}

const VolumeControl = ({ setVolume }) => {
  const [volume, _setVolume] = useState(-6)
  return <>
    <div style={{textAlign: 'center', width: '100%'}}>
      <input style={{writingMode: 'vertical-lr'}} type="range" min="-72" max="12"
             onChange={(e) => { setVolume(e.target.value); _setVolume(e.target.value) }} value={volume}></input>
      <div>{volume}</div>
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

const CodeEditor = ({ runCode }) => {
  const editor = useRef()
  const onMount = (ed => editor.current = ed)

  const onKeyDown = (ev) => {
    if (ev.keyCode == KEY_ENTER && ev.shiftKey) {
      const selection = editor.current.getSelection()
      let content = editor.current.getModel().getValueInRange(selection)
      if (content === "") {
        content = editor.current.getModel().getLineContent(selection.positionLineNumber)
      }
      runCode(content)
      ev.preventDefault()
    }
  }
  return <div onKeyDown={onKeyDown} style={{height: '100%'}}>
    <Editor defaultLanguage="python" onMount={onMount} onChange={() => console.log(editor.current)} />
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
  const runCode = useRef()
  const [finished, setFinished] = useState(null)
  const [focus, setFocus] = useState(null)

  let focusModule = null, focusName = null, focusResource = null
  if (focus !== null) {
    const [first, ...rest] = focus.split(".")
    focusModule = first
    focusName = rest.join(".")
    focusResource = resources[focusModule][focusName]
  }

  useEffect(() => {
    socket = new WebSocket("ws://localhost:8765")
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === "resources") {
        // TODO: s/streams/resources/g
        setStreams(data.resources_old)
        console.log(data.resources)
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
    <div className="layout">
      {/* Top bar */}
      <div className="menu">
        <button>
          <Icon name="menu" />
        </button>
      </div>
      <div className="title">
        {focus !== null &&
        <>
          {focusModule !== "__main__" && <span className="title-module">{focusModule}.</span>}
          <span>{focusName}</span>
        </>}
      </div>
      <div className="toolbar"></div>

      {/* Left sidebar */}
      <div className="volume">
        <VolumeControl setVolume={(db) => send({ cmd: "volume", volume: Math.pow(10, db/20) })} />
      </div>
      
      {/* Main content */}
      <ResourcePane resources={resources} focus={focus} setFocus={setFocus} />
      <div className="details">
        {/* TODO: Tiny controls in resource pane */}
        {focus !== null &&
        <Stream name={focus} stream={focusResource} finished={focus === finished} />}
      </div>
      <div className="editor">
        <CodeEditor runCode={runCode.current} />
      </div>
      <div className="repl">
        <REPL setAppendOutput={(f) => appendOutput.current = f} setRunCode={(f) => runCode.current = f} />
      </div>
    </div>
    /* <Settings doRefresh={() => send({ cmd: "refresh" })} /> */
  )
}

export default App
