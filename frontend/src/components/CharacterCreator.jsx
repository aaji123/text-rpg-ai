import { useState } from "react";
import HelpTip from "./HelpTip.jsx";

export const STAT_LABELS = {
  Xianxia: ["Strength", "Agility", "Constitution", "Comprehension", "Perception", "Willpower"],
  Fantasy: ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"],
  "Sci-Fi": ["Strength", "Agility", "Endurance", "Intelligence", "Perception", "Technical Skill"],
  Cyberpunk: ["Body", "Reflexes", "Technical Ability", "Intelligence", "Cool", "Empathy"],
};
export const BACKGROUND_TEMPLATES = {
  Xianxia: {
    "Sect Orphan": "Raised among the outer courtyards of a remote sect, you learned discipline by watching from the edges and dream of earning a place within its halls.",
    "Outer Disciple": "You are an outer disciple with modest resources, a few practical skills, and a determination to prove your worth to the sect.",
    "Village Healer": "You grew up tending to a mountain village, learning herbs and the quiet needs of ordinary people before cultivation called to you.",
    "Disgraced Heir": "Once heir to a respected family, you lost your standing after a public failure and now seek a chance to restore your name.",
  },
  Fantasy: {
    Farmhand: "You were raised on a modest farm, accustomed to hard work, changing seasons, and the close ties of a small community.",
    "Wandering Scholar": "You traveled between libraries and tutors, collecting fragments of history and learning to ask careful questions.",
    "Guild Apprentice": "You trained under a local guild, learning a useful craft while waiting for a chance to choose your own path.",
    "Fallen Noble": "Your family has lost its title and fortune, leaving you with a name to live up to and little else to rely on.",
  },
  "Sci-Fi": {
    "Corporate Spy": "You were trained to observe, blend in, and retrieve secrets inside the polished halls of a powerful corporation.",
    "Station Mechanic": "You grew up keeping a crowded orbital station running, learning its systems and the people who depend on them.",
    "Colony Medic": "You served a remote settlement where limited supplies made calm judgment and improvisation essential.",
    "Military Deserter": "You left military service after a mission crossed a line you could not accept, and now keep your past carefully guarded.",
  },
  Cyberpunk: {
    "Street Courier": "You learned the city's back routes delivering packages through neighborhoods where trust is scarce and speed matters.",
    "Corpo Defector": "You walked away from a corporate career with inside knowledge, a few contacts, and reasons to stay out of sight.",
    "Netrunner Apprentice": "You learned to navigate secure networks under a mentor who taught you to be patient, curious, and cautious.",
    "Clinic Tech": "You helped a neighborhood clinic stretch limited equipment and supplies while caring for people the city overlooks.",
  },
};
const POINT_BUDGET = 72;

/** Create the valid starter data shape for the currently selected genre. */
export function defaultCharacter(worldTemplate) {
  return {
    identity: { name: "", age: 18, background: "" },
    stats: Object.fromEntries((STAT_LABELS[worldTemplate] || STAT_LABELS.Fantasy).map((stat) => [stat, 10])),
    inventory: [],
  };
}

/** Collect a grounded identity, constrained stats, and metadata-rich inventory. */
export default function CharacterCreator({ worldTemplate, value, onChange }) {
  const [draftItem, setDraftItem] = useState({ name: "", kind: "Consumable", quantity: 1, max_durability: 10 });
  const stats = STAT_LABELS[worldTemplate] || STAT_LABELS.Fantasy;
  const backgrounds = BACKGROUND_TEMPLATES[worldTemplate] || BACKGROUND_TEMPLATES.Fantasy;
  const selectedBackground = Object.entries(backgrounds).find(([, text]) => text === value.identity.background)?.[0] || "custom";
  const pointsSpent = Object.values(value.stats).reduce((total, points) => total + Number(points), 0);

  /** Update one stat while enforcing the shared point-buy ceiling in the UI. */
  function changeStat(label, newValue) {
    const nextTotal = pointsSpent - Number(value.stats[label]) + Number(newValue);
    if (nextTotal <= POINT_BUDGET) onChange({ ...value, stats: { ...value.stats, [label]: Number(newValue) } });
  }

  /** Add a validated item with the fields required by its metadata tag. */
  function addItem() {
    const name = draftItem.name.trim();
    if (!name) return;
    const item = { id: `item-${Date.now()}`, name, kind: draftItem.kind, tags: [draftItem.kind] };
    if (draftItem.kind === "Consumable") item.quantity = Number(draftItem.quantity);
    if (draftItem.kind === "Durable") {
      item.max_durability = Number(draftItem.max_durability);
      item.durability = Number(draftItem.max_durability);
    }
    onChange({ ...value, inventory: [...value.inventory, item] });
    setDraftItem({ ...draftItem, name: "" });
  }

  return (
    <div className="character-creator">
      <section className="creator-section">
        <div className="creator-section-title"><div><span className="eyebrow">IDENTITY</span><h3>Who begins this story?</h3></div><span className="character-glyph">✧</span></div>
        <div className="identity-grid">
          <label><span className="label-with-help">Name<HelpTip text="The character name appears in the character sheet and story context sent to the AI." /></span><input value={value.identity.name} maxLength={80} onChange={(event) => onChange({ ...value, identity: { ...value.identity, name: event.target.value } })} placeholder="Character name" /></label>
          <label><span className="label-with-help">Age<HelpTip text="Sets the character's age for the story and may influence how NPCs react." /></span><input type="number" min="1" max="999" value={value.identity.age} onChange={(event) => onChange({ ...value, identity: { ...value.identity, age: Number(event.target.value) } })} /></label>
          <label className="wide-field"><span className="label-with-help">Background template<HelpTip text="Choose a local genre-specific origin to fill the text below, or choose Custom to write your own. Templates use no AI calls." /></span><select value={selectedBackground} onChange={(event) => onChange({ ...value, identity: { ...value.identity, background: backgrounds[event.target.value] || "" } })}><option value="custom">Custom</option>{Object.keys(backgrounds).map((template) => <option key={template} value={template}>{template}</option>)}</select><textarea rows="3" maxLength={1000} value={value.identity.background} onChange={(event) => onChange({ ...value, identity: { ...value.identity, background: event.target.value } })} placeholder="Choose a template or write your own background…" /></label>
        </div>
      </section>
      <section className="creator-section">
        <div className="creator-section-title"><div><span className="eyebrow">POINT BUY · {worldTemplate.toUpperCase()}</span><h3>Distribute your attributes</h3></div><span className={pointsSpent > POINT_BUDGET ? "point-count over" : "point-count"}>{pointsSpent} <small>/ {POINT_BUDGET}</small></span></div>
        <p className="creator-hint">Every stat starts at 10. Choose values from 3 to 18; no stat can fall below 3.</p>
        <div className="stat-grid">{stats.map((label) => <label key={label}><span className="label-with-help">{label}<HelpTip text={`This attribute shapes ${label.toLowerCase()}-related checks and the AI's assessment of your character's capabilities.`} /></span><select value={value.stats[label]} onChange={(event) => changeStat(label, event.target.value)}>{Array.from({ length: 16 }, (_, index) => index + 3).map((score) => <option key={score} value={score} disabled={pointsSpent - value.stats[label] + score > POINT_BUDGET}>{score}</option>)}</select></label>)}</div>
      </section>
      <section className="creator-section inventory-builder">
        <div className="creator-section-title"><div><span className="eyebrow">STARTING GEAR</span><h3>Pack your inventory</h3></div><span className="point-count">{value.inventory.length} <small>items</small></span></div>
        <div className="inventory-form"><label className="item-name-field"><span className="label-with-help">Item name<HelpTip text="Enter the starting item's name. Matching its name in a later action lets the backend track use or durability." /></span><input value={draftItem.name} maxLength={80} onChange={(event) => setDraftItem({ ...draftItem, name: event.target.value })} placeholder="Manual item name" /></label><label><span className="label-with-help">Type<HelpTip text="Consumables lose quantity, durable gear loses durability, and permanent items have no automatic limit." /></span><select value={draftItem.kind} onChange={(event) => setDraftItem({ ...draftItem, kind: event.target.value })}>{["Consumable", "Durable", "Permanent"].map((kind) => <option key={kind}>{kind}</option>)}</select></label>{draftItem.kind === "Consumable" && <label><span className="label-with-help">Quantity<HelpTip text="How many uses are available. Explicitly using the item decrements this count." /></span><input type="number" min="1" max="999" value={draftItem.quantity} onChange={(event) => setDraftItem({ ...draftItem, quantity: event.target.value })} /></label>}{draftItem.kind === "Durable" && <label><span className="label-with-help">Max durability<HelpTip text="Starting and maximum condition. The backend tracks wear when you describe damaging the item." /></span><input type="number" min="1" max="1000" value={draftItem.max_durability} onChange={(event) => setDraftItem({ ...draftItem, max_durability: event.target.value })} /></label>}<button type="button" disabled={!draftItem.name.trim()} onClick={addItem}>Add item</button></div>
        {value.inventory.length > 0 ? <ul className="inventory-list">{value.inventory.map((item) => <li key={item.id}><div><strong>{item.name}</strong><small>{item.kind}{item.kind === "Consumable" ? ` · Qty ${item.quantity}` : item.kind === "Durable" ? ` · Durability ${item.durability}/${item.max_durability}` : " · Permanent"}</small></div><button type="button" onClick={() => onChange({ ...value, inventory: value.inventory.filter((entry) => entry.id !== item.id) })} aria-label={`Remove ${item.name}`}>×</button></li>)}</ul> : <p className="empty-inventory">No starting items yet.</p>}
      </section>
    </div>
  );
}
