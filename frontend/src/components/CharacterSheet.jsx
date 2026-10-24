/** Display JSON-backed character state alongside its generated goal summaries. */
export default function CharacterSheet({ state, goals, plotPillars, worldTemplate }) {
  const identity = state?.identity || {};
  const resource = state?.resource || { current: 0, maximum: 0 };
  const inventory = state?.inventory || [];
  return (
    <section className="side-card character-card">
      <div className="side-title"><span><span className="eyebrow">YOUR CHARACTER</span><small className="template-label">{worldTemplate || state?.world_template}</small></span><span className="ornament">✧</span></div>
      <div className="sheet-section"><h3>Identity</h3><div className="sheet-row"><span>Name</span><strong>{identity.name || "Adventurer"}</strong></div><div className="sheet-row"><span>Age</span><strong>{identity.age ?? "—"}</strong></div><div className="sheet-row"><span>Realm</span><strong>{state?.realm_progress?.current || "Unranked"}</strong></div></div>
      <div className="sheet-section"><h3>Stats</h3>{Object.entries(state?.stats || {}).map(([label, value]) => <div className="sheet-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
      <div className="sheet-section"><h3>{state?.resource_label || "Resource"}</h3><div className="sheet-row"><span>Current</span><strong>{resource.current} / {resource.maximum}</strong></div></div>
      <div className="sheet-section"><h3>Inventory</h3>{inventory.length ? inventory.map((item) => <div className="sheet-row inventory-row" key={item.id}><span>{item.name}<small>{item.kind}</small></span><strong>{item.kind === "Consumable" ? `×${item.quantity}` : item.kind === "Durable" ? `${item.durability}/${item.max_durability}` : "∞"}</strong></div>) : <p className="sheet-note">No items</p>}</div>
      <div className="sheet-section"><h3>Relationships</h3>{(state?.relationships || []).length ? state.relationships.map((npc) => <div className="sheet-row" key={npc.name}><span>{npc.name}</span><strong>{npc.attitude}</strong></div>) : <p className="sheet-note">No key NPCs recorded</p>}</div>
      <div className="sheet-section"><h3>Technique library</h3>{(state?.techniques || []).length ? state.techniques.map((skill) => <div className="sheet-row" key={skill.name}><span>{skill.name}</span><strong>{skill.proficiency}</strong></div>) : <p className="sheet-note">No learned techniques</p>}</div>
      <div className="sheet-section goals"><h3>Lore bank</h3>{(state?.lore_bank || []).length ? state.lore_bank.map((entry) => <p key={entry.fact}>✦ {entry.fact}</p>) : <p className="sheet-note">No confirmed lore recorded</p>}</div>
      <div className="sheet-section goals"><h3>Active goals</h3>{goals.split("\n").filter((line) => line.startsWith("- ")).map((line) => <p key={line}>◇ {line.slice(2)}</p>)}</div>
      <div className="sheet-section goals"><h3>Plot pillars</h3>{plotPillars.split("\n").filter((line) => line.startsWith("- ") && !line.includes("No plot pillars")).map((line) => <p key={line}>✦ {line.slice(2)}</p>)}</div>
      <p className="sheet-note">This readable sheet is generated from the campaign's structured state.</p>
    </section>
  );
}
