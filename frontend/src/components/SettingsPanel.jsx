import HelpTip from "./HelpTip.jsx";

/** Persist campaign tone and rule preferences whenever the player changes them. */
export default function SettingsPanel({ settings, onChange, disabled }) {
  return (
    <section className="side-card settings-card">
      <div className="side-title"><span className="eyebrow">CAMPAIGN SETTINGS</span><span className="ornament">⚙</span></div>
      <label><span className="label-with-help">Difficulty<HelpTip text="Sets how challenging the AI makes uncertain actions and consequences." /></span><select disabled={disabled} value={settings.difficulty} onChange={(event) => onChange({ ...settings, difficulty: event.target.value })}>{["Easy", "Moderate", "Hard"].map((option) => <option key={option}>{option}</option>)}</select></label>
      <label><span className="label-with-help">Play mode<HelpTip text="Controls whether the AI leans on dice, narration, or a balance of both." /></span><select disabled={disabled} value={settings.mode} onChange={(event) => onChange({ ...settings, mode: event.target.value })}>{["Dice-heavy", "Narrative-heavy", "Hybrid"].map((option) => <option key={option}>{option}</option>)}</select></label>
      <label><span className="label-with-help">World power level<HelpTip text="Guides the scale of threats, abilities, and how quickly the AI advances your character." /></span><select disabled={disabled} value={settings.world_power_level || "Medium"} onChange={(event) => onChange({ ...settings, world_power_level: event.target.value })}>{["Low", "Medium", "High/Cosmic"].map((option) => <option key={option}>{option}</option>)}</select></label>
      <label><span className="label-with-help">Adventure tone<HelpTip text="Sets the emotional style and language used in upcoming narration." /></span><select disabled={disabled} value={settings.tone} onChange={(event) => onChange({ ...settings, tone: event.target.value })}>{["Gritty", "Heroic", "Mysterious", "Dark", "Whimsical", "Philosophical"].map((option) => <option key={option}>{option}</option>)}</select></label>
      <p className="settings-caption">Changes apply to the next narrator turn.</p>
    </section>
  );
}
