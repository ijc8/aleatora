import React, { useEffect, useState } from 'react';
import logo from './logo.svg';
import './App.css';

let socket = new WebSocket("ws://localhost:8765")
const send = (obj: any) => socket.send(JSON.stringify(obj))

window.onbeforeunload = () => {
  socket.onclose = () => {}
  socket.close()
}

function App() {
  const [state, setState] = useState({} as { [key: string]: number })

  useEffect(() => {
    socket.onmessage = e => setState(JSON.parse(e.data))
  }, [])

  return (
    <div className="App">
      <table>
        <tbody>
          {Object.entries(state).map(([key, value]) =>
            <tr><td>{key}</td><td>{value}</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

export default App
