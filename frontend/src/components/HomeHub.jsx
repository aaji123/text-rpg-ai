import { useRef, useState } from "react";

/** Present campaign continuation, local story management, and safe import. */
export default function HomeHub({ stories, recentStoryId, onCreate, onLoad, onDelete, onImport, onExport }) {
  const fileInput = useRef(null);
  const [importing, setImporting] = useState(false);
  const recentStory = stories.find((story) => story.id === recentStoryId) || stories[0];

  /** Validate the selected archive through the backend, then reset the input. */
  async function handleImport(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setImporting(true);
    try { await onImport(file); }
    finally { setImporting(false); }
  }

  return (
    <section className="home-hub">
      <div className="home-hero"><span className="eyebrow">YOUR PRIVATE STORY LIBRARY</span><h1>Every world starts somewhere.</h1><p>Create a new campaign or return to a story already in progress.</p>
        <div className="home-actions"><button className="primary" onClick={onCreate}>✦ &nbsp;Create a campaign</button>{recentStory && <button className="secondary-action" onClick={() => onLoad(recentStory.id)}>Continue {recentStory.name} →</button>}</div>
      </div>
      <div className="library-heading"><div><span className="eyebrow">STORY LIBRARY</span><h2>Your campaigns</h2></div><div><input ref={fileInput} className="visually-hidden" type="file" accept=".zip,application/zip" onChange={handleImport} /><button className="secondary-action" disabled={importing} onClick={() => fileInput.current?.click()}>{importing ? "Importing…" : "⇧ Import story"}</button></div></div>
      <p className="library-hint">Import a story ZIP shared by a friend. Archives are checked locally before any campaign files are saved.</p>
      {stories.length ? <div className="story-grid">{stories.map((story) => <article className="story-card" key={story.id}>
        <button className="story-card-main" onClick={() => onLoad(story.id)}><span className="story-card-mark">✧</span><strong>{story.name}</strong><small>Open campaign</small></button>
        <div className="story-card-actions"><button title="Download a shareable story ZIP" onClick={() => onExport(story)}>Export</button><button title="Delete this campaign and its local files" onClick={() => onDelete(story)}>Delete</button></div>
      </article>)}</div> : <div className="library-empty"><span>✧</span><p>No campaigns yet. Create one or import a story archive.</p></div>}
      <p className="home-privacy">Story folders remain on this machine unless you export or share them. Chat and example generation prompts are sent to Groq.</p>
    </section>
  );
}
