/** Show the Markdown character sheet as a readable, editable-source snapshot. */
export default function CharacterSheet({ character, goals }) {
  const sections = character.split(/\n(?=## )/).slice(1);
  return (
    <section className="side-card character-card">
      <div className="side-title"><span className="eyebrow">YOUR CHARACTER</span><span className="ornament">✧</span></div>
      {sections.map((section) => {
        const [heading, ...lines] = section.split("\n");
        return <div className="sheet-section" key={heading}><h3>{heading.replace(/^##\s*/, "")}</h3>{lines.filter((line) => line.startsWith("- ")).map((line) => {
          const [label, ...value] = line.slice(2).split(":");
          return <div className="sheet-row" key={line}><span>{label}</span><strong>{value.join(":").trim()}</strong></div>;
        })}</div>;
      })}
      <div className="sheet-section goals"><h3>Active goals</h3>{goals.split("\n").filter((line) => line.startsWith("- ")).map((line) => <p key={line}>◇ {line.slice(2)}</p>)}</div>
      <p className="sheet-note">Your character sheet is stored as Markdown in this story folder.</p>
    </section>
  );
}
