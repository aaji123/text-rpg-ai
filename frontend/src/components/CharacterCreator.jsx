import { useState } from "react";

export const STAT_LABELS = {
  Xianxia: ["Strength", "Agility", "Constitution", "Comprehension", "Perception", "Willpower"],
  Fantasy: ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"],
  "Sci-Fi": ["Strength", "Agility", "Endurance", "Intelligence", "Perception", "Technical Skill"],
  Cyberpunk: ["Body", "Reflexes", "Technical Ability", "Intelligence", "Cool", "Empathy"],
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
          <label>Name<input value={value.identity.name} maxLength={80} onChange={(event) => onChange({ ...value, identity: { ...value.identity, name: event.target.value } })} placeholder="Character name" /></label>
          <label>Age<input type="number" min="1" max="999" value={value.identity.age} onChange={(event) => onChange({ ...value, identity: { ...value.identity, age: Number(event.target.value) } })} /></label>
          <label className="wide-field">Starting background<textarea rows="3" maxLength={1000} value={value.identity.background} onChange={(event) => onChange({ ...value, identity: { ...value.identity, background: event.target.value } })} placeholder="A brief origin, occupation, or defining circumstance…" /></label>
        </div>
      </section>
      <section className="creator-section">
        <div className="creator-section-title"><div><span className="eyebrow">POINT BUY · {worldTemplate.toUpperCase()}</span><h3>Distribute your attributes</h3></div><span className={pointsSpent > POINT_BUDGET ? "point-count over" : "point-count"}>{pointsSpent} <small>/ {POINT_BUDGET}</small></span></div>
        <p className="creator-hint">Every stat starts at 10. Choose values from 3 to 18; no stat can fall below 3.</p>
        <div className="stat-grid">{stats.map((label) => <label key={label}>{label}<select value={value.stats[label]} onChange={(event) => changeStat(label, event.target.value)}>{Array.from({ length: 16 }, (_, index) => index + 3).map((score) => <option key={score} value={score} disabled={pointsSpent - value.stats[label] + score > POINT_BUDGET}>{score}</option>)}</select></label>)}</div>
      </section>
      <section className="creator-section inventory-builder">
        <div className="creator-section-title"><div><span className="eyebrow">STARTING GEAR</span><h3>Pack your inventory</h3></div><span className="point-count">{value.inventory.length} <small>items</small></span></div>
        <div className="inventory-form"><label className="item-name-field">Item name<input value={draftItem.name} maxLength={80} onChange={(event) => setDraftItem({ ...draftItem, name: event.target.value })} placeholder="Manual item name" /></label><label>Type<select value={draftItem.kind} onChange={(event) => setDraftItem({ ...draftItem, kind: event.target.value })}>{["Consumable", "Durable", "Permanent"].map((kind) => <option key={kind}>{kind}</option>)}</select></label>{draftItem.kind === "Consumable" && <label>Quantity<input type="number" min="1" max="999" value={draftItem.quantity} onChange={(event) => setDraftItem({ ...draftItem, quantity: event.target.value })} /></label>}{draftItem.kind === "Durable" && <label>Max durability<input type="number" min="1" max="1000" value={draftItem.max_durability} onChange={(event) => setDraftItem({ ...draftItem, max_durability: event.target.value })} /></label>}<button type="button" disabled={!draftItem.name.trim()} onClick={addItem}>Add item</button></div>
        {value.inventory.length > 0 ? <ul className="inventory-list">{value.inventory.map((item) => <li key={item.id}><div><strong>{item.name}</strong><small>{item.kind}{item.kind === "Consumable" ? ` · Qty ${item.quantity}` : item.kind === "Durable" ? ` · Durability ${item.durability}/${item.max_durability}` : " · Permanent"}</small></div><button type="button" onClick={() => onChange({ ...value, inventory: value.inventory.filter((entry) => entry.id !== item.id) })} aria-label={`Remove ${item.name}`}>×</button></li>)}</ul> : <p className="empty-inventory">No starting items yet.</p>}
      </section>
    </div>
  );
}
