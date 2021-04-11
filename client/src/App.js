import React, { useState, useRef, useEffect, useLayoutEffect } from 'react'
import { Provider, useSelector, useDispatch } from 'react-redux'
import store, { repl, socket, send } from './app/store'
import Editor from "@monaco-editor/react";
import './App.css'

// Data from Python process: map from variable name (String) => Stream info
// Stream info: { name: String, parameters: Parameters, children: undefined or Children }
// Parameter: map from String => Stream info or String (__repr__)
// Children: { streams: [Stream info], direction: String, separator: String }

const Icon = ({ name, style }) => <i className="material-icons" style={style}>{name}</i>

const Value = ({value}) => {
  if (typeof(value) === "string") {
    return value
  } else if (typeof(value) === "object") {
    return <Details {...value} />
  } else {
    throw "Expected object or string."
  }
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
  return <div>
    <h1 className="resource-name">{name}<span className="signature">{resource.signature}</span></h1><br/>
    <h2>Resource Type</h2>{resource.type}<br/><br/>
    <h2>Documentation</h2>{resource.doc}
  </div>
}

HelpTab.icon = "help_outline"

const EnvelopeTab = ({ name, resource }) => {
  const outer = useRef()
  const env = useRef()
  const points = resource.json
  useEffect(() => {
    if (!env.current) {
      const rect = outer.current.getBoundingClientRect()
      env.current = new Nexus.Envelope('#envelope', {
        size: [rect.width, rect.height],
        points: (points === undefined ? [{x: 0, y: 0}] : points.map(([x, y]) => ({x, y})))
      })
    }
  }, [])

  useLayoutEffect(() => {
    const updateSize = () => {
      const rect = outer.current.getBoundingClientRect()
      env.current.resize(rect.width, rect.height)
    }
    window.addEventListener('resize', updateSize)
    // updateSize()
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  return <div className="envelope-tab">
    <div className="envelope-toolbar">
      <span className="needs-better-name">... envelope duration ...</span>
      <button onClick={() => send({ cmd: "save", type: "envelope", name, payload: env.current.points })}><Icon name="save" /></button>
    </div>
    <div ref={outer} id="envelope" style={{flexGrow: 1, overflow: 'hidden', minHeight: 0}} />
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
    roll.current.sequence = resource.json.map(([start, length, pitch]) => ({t: start, g: length, n: pitch}))
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
  return <textarea ref={textbox} className="speech" type="text" defaultValue={resource.json} onKeyPress={onKeyPress} />
}

SpeechTab.icon = "chat"

// For now, this is many-to-one; later it might be many-to-many.
const tabMap = {
  "envelope": EnvelopeTab,
  "sequence": SequenceTab,
  "speech": SpeechTab,
}

const ResourceDetails = ({ name, resource, playing, setPlaying }) => {
  const [_expanded, setExpanded] = useState(-1)

  let tabs = [InspectorTab]
  if (tabMap[resource.name] !== undefined) {
    tabs.push(tabMap[resource.name])
  }
  tabs.push(HelpTab)
  
  // Make sure this stays in-bounds when switching between resources.
  const expanded = Math.min(_expanded, tabs.length - 1)

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
          console.log(name)
          setPlaying(!playing)
        }}>
          <Icon name={playing ? "pause" : "play_arrow"} />
        </button>
        {resource.instrument &&
        <button className="resource-control" onClick={() => send({ cmd: "record", name })}>
          <Icon name="fiber_manual_record" style={{color: "red", fontSize: "18px", paddingLeft: "2px", paddingBottom: "1px"}} />
        </button>}
        <button className="resource-control" style={{borderRight: '1px solid black'}} onClick={() => {
          send({ cmd: "stop", name })
          setPlaying(false)
        }}>
          <Icon name="stop" />
        </button>
        <div className="flex-spacer">{/* Maybe seek controls go here? */}</div>
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
        return <div className="resource-content"><Tab name={name} resource={resource} /></div>
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

const REPL = ({ setRunCode }) => {
  const dispatch = useDispatch()
  const contents = useSelector(repl.selectContents)
  const inputStart = useSelector(repl.selectInputStart)
  const textarea = useRef()

  useEffect(() => {
    textarea.current.scrollTop = textarea.current.scrollHeight
  }, [contents])

  const onKeyDown = (event) => {
    if (event.keyCode === KEY_BACKSPACE && (textarea.current.selectionStart <= inputStart)) {
      event.preventDefault()
    } else if (event.keyCode === KEY_DELETE && (textarea.current.selectionStart < inputStart)) {
      event.preventDefault()
    } else if (event.keyCode === KEY_LEFT && (textarea.current.selectionStart <= inputStart)) {
      event.preventDefault()
    } else if (event.keyCode === KEY_HOME) {
      event.preventDefault()
      textarea.current.selectionStart = inputStart
      if (!event.shiftKey) textarea.current.selectionEnd = inputStart
    } else if (event.keyCode === KEY_UP) {
      event.preventDefault()
      if (historyIndex > 0) {
        historyIndex--
        dispatch(repl.setContents(contents.slice(0, inputStart) + history[historyIndex].modified))
      }
    } else if (event.keyCode === KEY_DOWN) {
      event.preventDefault()
      if (historyIndex < history.length - 1) {
        historyIndex++
        dispatch(repl.setContents(contents.slice(0, inputStart) + history[historyIndex].modified))
      }
    }
  }

  const onChange = (event) => {
    history[historyIndex].modified = event.target.value.slice(inputStart)
    dispatch(repl.setContents(event.target.value))
  }

  const onKeyPress = (event) => {
    if (textarea.current.selectionStart < inputStart || event.keyCode === 13) {
      event.preventDefault()
    }

    if (event.charCode === KEY_ENTER) {
      textarea.current.selectionStart = textarea.current.selectionEnd = contents.length
      const code = contents.slice(inputStart)
      console.log("Submitting REPL code:", code)
      send({ cmd: "exec", mode: "single", code })
      dispatch(repl.setInputStart(contents.length + 1))
      console.log("sent successfully")
      history[history.length - 1].original = history[history.length - 1].modified = history[historyIndex].modified
      history[historyIndex].modified = history[historyIndex].original
      history.push({original: '', modified: ''})
      historyIndex = history.length - 1
    }
  }

  const onPasteOrCut = (event) => {
    if (textarea.current.selectionStart < inputStart) {
      event.preventDefault()
    }
  }

  return <textarea ref={textarea} spellCheck={false} value={contents} onChange={onChange} onKeyDown={onKeyDown} onKeyPress={onKeyPress} onPaste={onPasteOrCut} onCut={onPasteOrCut} />
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

const Resource = ({ name, fullName, value, focus, setFocus, playing, setPlaying }) => {
  const icon = (value.type === "stream" ? "water" : (value.instrument ? "piano" : "microwave"))
  return <li onClick={setFocus} className={focus ? "focused" : ""}>
    <span className="resource-name"><Icon name={icon} /> {name}</span>
    {value.type === "stream" &&
    <button onClick={() => {
      send({ cmd: playing ? "pause" : "play", name: fullName })
      setPlaying(!playing)
    }} className="resource-pane-button"><Icon name={playing ? "pause" : "play_arrow"} /></button>}
  </li>
}

const Module = ({ name, resources, expand, setExpand, focus, setFocus, playing, setPlaying }) => (
  <li>
    <div className="module-header">
      <button className="module-toggle" onClick={() => setExpand(!expand)}><Icon name={`expand_${expand ? 'less' : 'more'}`} /></button>
      <span className="module-name">{name}</span>
    </div>
    {expand &&
    <ul className="resource-list">
      {Object.entries(resources).map(([resourceName, value]) => {
        const fullName = `${name}.${resourceName}`
        return <Resource key={resourceName} name={resourceName} fullName={fullName} value={value}
                         focus={focus === fullName} setFocus={() => setFocus(fullName)}
                         playing={playing[fullName]} setPlaying={(p) => setPlaying({...playing, [fullName]: p})} />
      })}
    </ul>}
  </li>
)

const ResourcePane = ({ resources, focus, setFocus, playing, setPlaying }) => {
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
          <Module key={name} name={name} resources={value}
                  expand={expand[name] === undefined ? true : expand[name]} setExpand={(e) => setExpand({ ...expand, [name]: e })}
                  focus={focus} setFocus={setFocus}
                  playing={playing} setPlaying={setPlaying} />)}
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

const CodeEditor = ({ editor }) => {
  const dispatch = useDispatch()

  const onKeyDown = (ev) => {
    if (ev.keyCode == KEY_ENTER && ev.shiftKey) {
      const selection = editor.current.getSelection()
      let content = editor.current.getModel().getValueInRange(selection)
      if (content === "") {
        content = editor.current.getModel().getLineContent(selection.positionLineNumber)
      }
      dispatch(repl.runCode(content))
      ev.preventDefault()
    }
  }

  return <div onKeyDown={onKeyDown} style={{height: '100%'}}>
    <Editor defaultLanguage="python" onMount={ed => editor.current = ed} />
  </div>
}

const ProjectBar = ({ create, open, save }) => {
  const [name, setName] = useState("Untitled Project")
  const [editing, setEditing] = useState(false)

  const finish = (e) => {
    setName(e.target.textContent)
    setEditing(false)
  }

  return <div className="project">
    <div>
      <button onClick={() => { create(); setName("A big blank project") }}><Icon name="post_add" /></button>
      <button onClick={() => open(name)}><Icon name="folder_open" /></button>
      <button onClick={() => save(name)}><Icon name="save" /></button>
    </div>
    {editing
    ? <div style={{justifyContent: 'center', display: 'flex', alignItems: 'center'}} contentEditable onKeyDown={e => { if (e.key === "Enter") finish(e) }} onBlur={finish}>{name}</div>
    : <div style={{justifyContent: 'center', display: 'flex', alignItems: 'center'}} onClick={() => setEditing(true)}>{name}</div>}
  </div>
}


const Nexus = window.Nexus


const App = () => {
  const dispatch = useDispatch()
  const replContents = useSelector(repl.selectContents)

  const editor = useRef()
  const [resources, setResources] = useState({})
  const [playing, setPlaying] = useState({})
  const [focus, setFocus] = useState(null)
  const [usage, setUsage] = useState({cpu: "?", memory: "?"})

  const create = () => {
    dispatch(repl.setContents(">>> "))
    dispatch(repl.setInputStart(4))
    editor.current.getModel().setValue("")
  }

  const open = (name) => {
    send({cmd: "openproject", name})
  }

  const save = (name) => {
    send({cmd: "saveproject", name, editor: editor.current.getModel().getValue(), repl: replContents})
  }

  let focusModule = null, focusName = null, focusResource = null
  if (focus !== null) {
    const [first, ...rest] = focus.split(".")
    focusModule = first
    focusName = rest.join(".")
    focusResource = resources[focusModule][focusName]
  }

  useEffect(() => {
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === "resources") {
        console.log(data.resources)
        setResources(data.resources)
      } else if (data.type === "output") {
        dispatch(repl.appendOutput(data.output))
      } else if (data.type === "finish") {
        setPlaying({...playing, [data.name]: false})
      } else if (data.type === "project") {
        editor.current.getModel().setValue(data.editor)
        // TODO: Restore REPL history.
        dispatch(repl.setContents(data.repl))
        dispatch(repl.setInputStart(data.repl.length))
      } else if (data.type === "usage") {
        setUsage({cpu: data.cpu.toFixed(1) + "%", memory: +(Math.round(data.memory + "e+2")  + "e-2") + " MB"})
      } else if (data.type === "error") {
        console.log(data)
      }
    }
  }, [playing])

  return <Provider store={store}>
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

      <ProjectBar create={create} open={open} save={save} />

      {/* Left sidebar */}
      <div className="volume">
        <VolumeControl setVolume={(db) => send({ cmd: "volume", volume: Math.pow(10, db/20) })} />
      </div>
      
      {/* Main content */}
      <ResourcePane resources={resources} focus={focus} setFocus={setFocus} playing={playing} setPlaying={setPlaying} />
      <div className="details">
        {focus !== null &&
        <ResourceDetails name={focus} resource={focusResource}
                         playing={playing[focus]} setPlaying={(p) => setPlaying({...playing, [focus]: p})} />}
      </div>
      <div className="editor">
        <CodeEditor editor={editor} />
      </div>
      <div className="repl">
        <REPL />
      </div>
      <div className="status">
        <div style={{width: "3em", textAlign: "right"}}>{usage.cpu}</div>&nbsp;/ {usage.memory}
      </div>
    </div>
  </Provider>
    /* <Settings doRefresh={() => send({ cmd: "refresh" })} /> */
}

export default App
