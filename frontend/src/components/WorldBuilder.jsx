import { useRef, useState } from "react";
import HelpTip from "./HelpTip.jsx";

const CULTIVATION_REALMS = [
  ["Body Tempering", "Qi Refining", "Foundation Establishment", "Core Formation", "Golden Core"],
  ["Nascent Soul", "Soul Formation", "Divine Transformation", "Void Refinement", "Integration"],
  ["True Immortal", "Heavenly Immortal", "Golden Immortal"],
  ["Immortal King", "Immortal Emperor", "Celestial Immortal", "Dao Lord", "Eternal Sovereign"],
  ["Heavenly Dao Master", "Saint/Sage", "Supreme Saint", "Chaos Realm", "Universal Creator", "Origin Ancestor"],
];
export const REALM_HIERARCHIES = {
  Xianxia: ["Mortal/Beginner", ...CULTIVATION_REALMS.flatMap((group) => group.flatMap((realm) => ["Early", "Mid", "Late"].map((stage) => `${realm} — ${stage}`)))],
  Fantasy: ["Commoner", "Novice", "Adept", "Expert", "Master", "Legendary", "Mythic"],
  "Sci-Fi": ["Tier 0: Civilian", "Tier 1: Enhanced", "Tier 2: Operative", "Tier 3: Elite", "Tier 4: Apex", "Tier 5: Posthuman"],
  Cyberpunk: ["Civilian", "Streetwise", "Professional", "Elite", "Corporate Legend", "Night City Myth"],
};

/** Build genre defaults once so users can adjust their progression ladder. */
export function defaultWorldSettings(worldTemplate) {
  const realmHierarchy = [...(REALM_HIERARCHIES[worldTemplate] || REALM_HIERARCHIES.Fantasy)];
  return { setting_description: "", plot_pillars: [], tone: "Heroic", mode: "Hybrid", world_power_level: "Medium", starting_plane: "Mortal Plane", house_rules: "", atmosphere: "", realm_hierarchy: realmHierarchy, highest_power_level: realmHierarchy.at(-1) };
}

/** Collect setting, tone, power ceiling, realms, anchors, and cached brainstorms. */
export default function WorldBuilder({ worldTemplate, value, onChange, onBrainstorm, onGenerateExample }) {
  const cache = useRef(new Map());
  const exampleCache = useRef(new Map());
  const [idea, setIdea] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pillarDraft, setPillarDraft] = useState("");
  const [generating, setGenerating] = useState("");
  const realmText = value.realm_hierarchy.join("\n");

  /** Reuse suggestions for the same idea and exact world context in this wizard. */
  async function brainstorm() {
    const cleanIdea = idea.trim();
    if (cleanIdea.length < 3) return setError("Enter a short plot point to brainstorm.");
    const key = JSON.stringify([cleanIdea.toLocaleLowerCase(), worldTemplate, value.setting_description, value.plot_pillars, value.realm_hierarchy, value.highest_power_level, value.world_power_level, value.starting_plane, value.house_rules, value.atmosphere, value.tone, value.mode]);
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

  /** Generate or reuse a short sample without overwriting unrelated fields. */
  async function generateExample(field) {
    const generationSettings = { ...value, [field]: "" };
    const key = JSON.stringify([field, worldTemplate, generationSettings]);
    if (exampleCache.current.has(key)) {
      onChange({ ...value, [field]: exampleCache.current.get(key) });
      return;
    }
    setGenerating(field); setError("");
    try {
      const example = await onGenerateExample(field, { ...generationSettings, world_template: worldTemplate });
      exampleCache.current.set(key, example);
      onChange({ ...value, [field]: example });
    } catch (reason) { setError(reason.message); }
    finally { setGenerating(""); }
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
        <label className="builder-field"><span className="label-with-help">Where and when does the story begin?<HelpTip text="Describe the opening location and time period. The AI uses this as the first scene's setting." /></span><textarea rows="4" maxLength={2000} value={value.setting_description} onChange={(event) => onChange({ ...value, setting_description: event.target.value })} placeholder="A mountain sect during the first snowfall of the year…" /><button className="generate-example" type="button" disabled={!!generating} onClick={() => generateExample("setting_description")}>{generating === "setting_description" ? "Generating…" : "✦ Generate example"}</button></label>
        <div className="builder-selects"><label><span className="label-with-help">Adventure tone<HelpTip text="Sets the emotional style and word choice the AI uses while narrating." /></span><select value={value.tone} onChange={(event) => onChange({ ...value, tone: event.target.value })}>{["Gritty", "Heroic", "Mysterious", "Dark", "Whimsical", "Philosophical"].map((tone) => <option key={tone}>{tone}</option>)}</select></label><label><span className="label-with-help">Play mode<HelpTip text="Controls how often the AI calls for dice versus resolving actions through the story." /></span><select value={value.mode} onChange={(event) => onChange({ ...value, mode: event.target.value })}>{["Dice-heavy", "Narrative-heavy", "Hybrid"].map((mode) => <option key={mode}>{mode}</option>)}</select></label><label><span className="label-with-help">World power<HelpTip text="Sets the overall scale of abilities, threats, and character advancement." /></span><select value={value.world_power_level} onChange={(event) => onChange({ ...value, world_power_level: event.target.value })}>{["Low", "Medium", "High/Cosmic"].map((level) => <option key={level}>{level}</option>)}</select></label></div>
        <div className="builder-selects ceiling-selects"><label><span className="label-with-help">Starting plane<HelpTip text="Names the initial world layer or dimension. The AI uses it to ground early locations and travel." /></span><input value={value.starting_plane} maxLength={100} onChange={(event) => onChange({ ...value, starting_plane: event.target.value })} placeholder="Mortal Plane" /></label></div>
        <label className="builder-field"><span className="label-with-help">House rules<HelpTip text="Add custom rules or boundaries the AI should follow throughout the campaign." /></span><textarea rows="3" maxLength={2000} value={value.house_rules} onChange={(event) => onChange({ ...value, house_rules: event.target.value })} placeholder="Rules the narrator should always follow…" /><button className="generate-example" type="button" disabled={!!generating} onClick={() => generateExample("house_rules")}>{generating === "house_rules" ? "Generating…" : "✦ Generate example"}</button></label>
        <label className="builder-field"><span className="label-with-help">Atmosphere notes<HelpTip text="Describe sensory details, pacing, or mood. The AI reflects these in its prose." /></span><textarea rows="2" maxLength={2000} value={value.atmosphere} onChange={(event) => onChange({ ...value, atmosphere: event.target.value })} placeholder="Sensory details, pacing, or mood…" /><button className="generate-example" type="button" disabled={!!generating} onClick={() => generateExample("atmosphere")}>{generating === "atmosphere" ? "Generating…" : "✦ Generate example"}</button></label>
      </section>
      <section className="creator-section">
        <div className="creator-section-title"><div><span className="eyebrow">POWER PROGRESSION</span><h3>Realm hierarchy</h3></div><span className="character-glyph">↗</span></div>
        <p className="creator-hint">One rank per line, ordered from the character's starting level to the world's peak.</p>
        <label className="builder-field"><span className="label-with-help">World realms<HelpTip text="List ranks from the starting stage to the world's peak, one per line. These guide progression and threat scale." /></span><textarea rows="9" maxLength={12000} value={realmText} onChange={(event) => updateRealms(event.target.value)} /></label>
        <div className="builder-selects ceiling-selects"><label><span className="label-with-help">Highest power level<HelpTip text="Sets the strongest rank or entity allowed in the world. The AI should keep it distant until story progress supports it." /></span><select value={value.highest_power_level} onChange={(event) => onChange({ ...value, highest_power_level: event.target.value })} disabled={!value.realm_hierarchy.length}>{value.realm_hierarchy.map((realm) => <option key={realm}>{realm}</option>)}</select></label></div>
        <small className="ceiling-note">This is the world's ceiling. The narrator will foreshadow distant tiers instead of introducing their strongest beings early.</small>
      </section>
      <section className="creator-section">
        <div className="creator-section-title"><div><span className="eyebrow">NARRATIVE ANCHORS</span><h3>Plot pillars</h3></div><span className="point-count">{value.plot_pillars.length}<small> / 12</small></span></div>
        <div className="pillar-entry"><label className="pillar-input-label"><span className="label-with-help">Plot pillar<HelpTip text="A long-term story goal the AI can seed naturally. Keep each pillar under 160 characters." /></span><input value={pillarDraft} maxLength={160} onChange={(event) => setPillarDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addPillar(); } }} placeholder="e.g. Meet a rival at the sect trials" /><small className="character-counter">{pillarDraft.length} / 160 characters</small></label><button type="button" onClick={() => addPillar()}>Add</button></div>
        <div className="brainstorm-inline"><label><span className="label-with-help">Or expand a vague idea<HelpTip text="The AI uses this idea and your world settings to return three optional plot pillars, each kept within 160 characters." /></span><input value={idea} maxLength={1000} onChange={(event) => setIdea(event.target.value)} placeholder="A lucky encounter, a mysterious inheritance…" /></label><button type="button" onClick={brainstorm} disabled={loading}>{loading ? "Thinking…" : "✦ Brainstorm"}</button></div>
        {error && <p className="wizard-error" role="alert">{error}</p>}
        {suggestions.length > 0 && <div className="world-suggestions">{suggestions.map((suggestion) => <button type="button" key={suggestion} disabled={value.plot_pillars.includes(suggestion)} onClick={() => addPillar(suggestion)}><span>＋</span>{suggestion}</button>)}</div>}
        <ul className="anchor-list">{value.plot_pillars.map((pillar) => <li key={pillar}><span>◇</span>{pillar}<button type="button" aria-label={`Remove ${pillar}`} onClick={() => onChange({ ...value, plot_pillars: value.plot_pillars.filter((item) => item !== pillar) })}>×</button></li>)}</ul>
      </section>
    </div>
  );
}
