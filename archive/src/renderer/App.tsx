import React, { useEffect, useState } from 'react'

declare global {
  interface Window {
    electronAPI?: {
      openFolder: () => Promise<string | null>
    }
  }
}

export default function App(){
  const [folder, setFolder] = useState('./ROMs')
  const [sections, setSections] = useState<string[]>([])
  const [games, setGames] = useState<any[]>([])

  useEffect(()=>{
    fetch('/api/sections').then(r=>r.json()).then(j=>setSections(j.sections || []))
  },[])

  async function init(){
    const res = await fetch('/api/init', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({folder})})
    const j = await res.json()
    if(j.status === 'root'){
      // if root, pick first console by default
      if(j.consoles && j.consoles.length) setFolder(j.root + '/' + j.consoles[0])
      return
    }
  }

  async function pickFolder(){
    const p = await window.electronAPI?.openFolder()
    if(p) setFolder(p)
  }

  async function loadSection(s:string){
    const r = await fetch(`/api/section/${s}?folder=${encodeURIComponent(folder)}`)
    const j = await r.json()
    setGames(j.games || [])
  }

  return (
    <div style={{padding:20}}>
      <h1>Vimms Desktop (Electron) — MVP</h1>
      <div>
        <input value={folder} onChange={e=>setFolder(e.target.value)} size={60} />
        <button onClick={init}>Init</button>
        <button onClick={pickFolder}>Select folder</button>
      </div>
      <div style={{marginTop:20}}>
        <strong>Sections</strong>
        <div>
          {sections.map(s=> <button key={s} onClick={()=>loadSection(s)} style={{marginRight:6}}>{s}</button>)}
        </div>
      </div>
      <div style={{marginTop:20}}>
        <h2>Games</h2>
        <table>
          <thead><tr><th>Name</th><th>ID</th><th>Present</th></tr></thead>
          <tbody>
            {games.map(g=> <tr key={g.game_id}><td>{g.name}</td><td>{g.game_id}</td><td>{String(g.present)}</td></tr>)}
          </tbody>
        </table>
      </div>
    </div>
  )
}
