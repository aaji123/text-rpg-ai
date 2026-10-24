import { useRef, useState } from "react";

export const REALM_HIERARCHIES = {
  Xianxia: ["Body Tempering", "Qi Condensation", "Foundation Establishment", "Core Formation", "Nascent Soul", "Spirit Severing", "Dao Integration", "Tribulation Transcendence", "Immortal"],
  Fantasy: ["Commoner", "Novice", "Adept", "Expert", "Master", "Legendary", "Mythic"],
  "Sci-Fi": ["Tier 0: Civilian", "Tier 1: Enhanced", "Tier 2: Operative", "Tier 3: Elite", "Tier 4: Apex", "Tier 5: Posthuman"],
  Cyberpunk: ["Civilian", "Streetwise", "Professional", "Elite", "Corporate Legend", "Night City Myth"],
};

/** Build genre defaults once so users can adjust their progression ladder. */
export function defaultWorldSettings(worldTemplate) {
  const realmHierarchy = [...(REALM_HIERARCHIES[worldTemplate] || REALM_HIERARCHIES.Fantasy)];
  return { setting_description: "", plot_pillars: [], tone: "Heroic", mode: "Hybrid", world_power_level: "Medium", realm_hierarchy: realmHierarchy, highest_power_level: realmHierarchy.at(-1) };
}

/** Collect setting, tone, power ceiling, realms, anchors, and cached brainstorms. */
export default function WorldBuilder({ worldTemplate, value, onChange, onBrainstorm }) {
  const cache = useRef(new Map());
  const [idea, setIdea] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pillarDraft, setPillarDraft] = useState("");
  const realmText = value.realm_hierarchy.join("\n");

  /** Reuse suggestions for the same idea and exact world context in this wizard. */
  async function brainstorm() {
    const cleanIdea = idea.trim();
    if (cleanIdea.length < 3) return setError("Enter a short plot point to brainstorm.");
    const key = JSON.stringify([cleanIdea.toLocaleLowerCase(), worldTemplate, value.setting_description, value.plot_pillars, value.realm_hierarchy, value.highest_power_level, value.world_power_level, value.tone, value.mode]);
    if (cache.current.has(key)) {
      setError("");
      setSuggestions(cache.current.get(key));
      return;
    }
    setLoading(true); setError("");
    try {
      const result = await onBrainstorm(cleanIdea, { ...value, world_template: worldTemplate });
      cache.current.set(key, result);
      setSuggestions(result);
    } catch (reason) { setError(reason.message); }
    finally { setLoading(false); }
  }

  /** Add an optional plot anchor from typed text or one-click suggestions. */
  function addPillar(text = pillarDraft) {
    const cleanText = text.trim();
    if (!cleanText || value.plot_pillars.includes(cleanText)) return;
    if (cleanText.length > 160 || value.plot_pillars.length >= 12) return setError("Use up to 12 plot pillars, each no longer than 160 characters.");
    onChange({ ...value, plot_pillars: [...value.plot_pillars, cleanText] });
    setPillarDraft(""); setError("");
  }

  /** Update the editable hierarchy and reset its ceiling if the chosen rank vanishes. */
  function updateRealms(text) {
    const realms = text.split("\n").map((realm) => realm.trim()).filter(Boolean);
    const highest = realms.includes(value.highest_power_level) ? value.highest_power_level : realms.at(-1) || "";
    onChange({ ...value, realm_hierarchy: realms, highest_power_level: highest });
  }

  return (
    <div className="world-builder">
      <section className="creator-section">
        <div className="creator-section-title"><div><span className="eyebrow">WORLD BUILDING · {worldTemplate.toUpperCase()}</span><h3>Set the opening scene</h3></div><span className="character-glyph">⌖</span></div>
        <label className="builder-field">Where and when does the story begin?<textarea rows="4" maxLength={2000} value={value.setting_description} onChange={(event) => onChange({ ...value, setting_description: event.target.value })} placeholder="A mountain sect during the first snowfall of the year…" /></label>
        <div className="builder-selects"><label>Adventure tone<select value={value.tone} onChange={(event) => onChange({ ...value, tone: event.target.value })}>{["Grim", "Heroic", "Mystery"].map((tone) => <option key={tone}>{tone}</option>)}</select></label><label>Play mode<select value={value.mode} onChange={(event) => onChange({ ...value, mode: event.target.value })}>{["Dice-heavy", "Narrative-heavy", "Hybrid"].map((mode) => <option key={mode}>{mode}</option>)}</select></label><label>World power<select value={value.world_power_level} onChange={(event) => onChange({ ...value, world_power_level: event.target.value })}>{["Low", "Medium", "High/Cosmic"].map((level) => <option key={level}>{level}</option>)}</select></label></div>
      </section>
      <section className="creator-section">
        <div className="creator-section-title"><div><span className="eyebrow">POWER PROGRESSION</span><h3>Realm hierarchy</h3></div><span className="character-glyph">↗</span></div>
        <p className="creator-hint">One rank per line, ordered from the character's starting level to the world's peak.</p>
        <label className="builder-field">World realms<textarea rows="5" value={realmText} onChange={(event) => updateRealms(event.target.value)} /></label>
        <div className="builder-selects ceiling-selects"><label>Highest power level<select value={value.highest_power_level} onChange={(event) => onChange({ ...value, highest_power_level: event.target.value })} disabled={!value.realm_hierarchy.length}>{value.realm_hierarchy.map((realm) => <option key={realm}>{realm}</option>)}</select></label></div>
        <small className="ceiling-note">This is the world's ceiling. The narrator will foreshadow distant tiers instead of introducing their strongest beings early.</small>
      </section>
      <section className="creator-section">
        <div className="creator-section-title"><div><span className="eyebrow">NARRATIVE ANCHORS</span><h3>Plot pillars</h3></div><span className="point-count">{value.plot_pillars.length}<small> / 12</small></span></div>
        <div className="pillar-entry"><input value={pillarDraft} maxLength={160} onChange={(event) => setPillarDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addPillar(); } }} placeholder="e.g. Meet a rival at the sect trials" /><button type="button" onClick={() => addPillar()}>Add</button></div>
        <div className="brainstorm-inline"><label>Or expand a vague idea<input value={idea} maxLength={1000} onChange={(event) => setIdea(event.target.value)} placeholder="A lucky encounter, a mysterious inheritance…" /></label><button type="button" onClick={brainstorm} disabled={loading}>{loading ? "Thinking…" : "✦ Brainstorm"}</button></div>
        {error && <p className="wizard-error" role="alert">{error}</p>}
        {suggestions.length > 0 && <div className="world-suggestions">{suggestions.map((suggestion) => <button type="button" key={suggestion} disabled={value.plot_pillars.includes(suggestion)} onClick={() => addPillar(suggestion)}><span>＋</span>{suggestion}</button>)}</div>}
        <ul className="anchor-list">{value.plot_pillars.map((pillar) => <li key={pillar}><span>◇</span>{pillar}<button type="button" aria-label={`Remove ${pillar}`} onClick={() => onChange({ ...value, plot_pillars: value.plot_pillars.filter((item) => item !== pillar) })}>×</button></li>)}</ul>
      </section>
    </div>
  );
}
